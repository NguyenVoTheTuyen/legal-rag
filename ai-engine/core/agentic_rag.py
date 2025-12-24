"""
Module Agentic RAG sử dụng LangGraph để tạo hệ thống RAG thông minh với khả năng:
- Tự động quyết định khi nào cần tìm kiếm
- Tinh chỉnh truy vấn nếu cần
- Thực hiện tìm kiếm nhiều bước
- Tạo câu trả lời dựa trên kết quả
"""

import sys
from pathlib import Path
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from operator import add

# Thêm thư mục ai-engine vào path
current_file = Path(__file__).resolve()
ai_engine_dir = current_file.parent.parent
sys.path.insert(0, str(ai_engine_dir))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_models import ChatOllama

# Import các module hiện có
from core.search import LegalSearch
from core.llm_generator import OllamaGenerator
from core.prompt_templates import PromptTemplates

# Import web search (optional)
try:
    from core.web_search import LegalWebSearch
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    LegalWebSearch = None


# Helper function để detect câu hỏi về số liệu cụ thể
def _contains_specific_data_query(question: str) -> bool:
    """
    Kiểm tra xem câu hỏi có yêu cầu số liệu cụ thể không.
    
    Args:
        question: Câu hỏi cần kiểm tra
        
    Returns:
        True nếu câu hỏi về số liệu cụ thể
    """
    keywords = [
        "bao nhiêu", "mức", "tỷ lệ", "%", "phần trăm",
        "số tiền", "tiền", "lương", "ngày", "tháng", "năm",
        "hiện nay", "mới nhất", "2024", "2025",
        "cụ thể", "chính xác", "đúng"
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in keywords)


class AgentState(TypedDict):
    """State của agent trong workflow."""
    question: str  # Câu hỏi gốc
    query: str  # Query hiện tại (có thể được refine)
    search_results: Annotated[List[Dict[str, Any]], add]  # Kết quả tìm kiếm nội bộ
    web_results: Annotated[List[Dict[str, Any]], add]  # Kết quả tìm kiếm web
    answer: Optional[str]  # Câu trả lời cuối cùng
    iteration: int  # Số lần lặp
    max_iterations: int  # Số lần lặp tối đa
    needs_refinement: bool  # Có cần refine query không
    should_continue: bool  # Có nên tiếp tục tìm kiếm không
    use_web_search: bool  # Có sử dụng web search không


class LegalRAGAgent:
    """Agent RAG cho hệ thống pháp lý sử dụng LangGraph."""
    
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "legal_documents",
        ollama_url: str = "http://127.0.0.1:11434",
        ollama_model: str = "llama3.2",
        embedding_model: str = "bkai-foundation-models/vietnamese-bi-encoder",
        max_iterations: int = 3,
        top_k: int = 3,
        searxng_url: Optional[str] = None,
        enable_web_search: bool = True,  # Changed to True - auto-enable web search
        prompt_templates: Optional[PromptTemplates] = None
    ):
        """
        Khởi tạo LegalRAGAgent.
        
        Args:
            qdrant_url: URL của Qdrant server
            collection_name: Tên collection trong Qdrant
            ollama_url: URL của Ollama server
            ollama_model: Tên model Ollama
            embedding_model: Tên model embedding
            max_iterations: Số lần lặp tối đa
            top_k: Số lượng kết quả tìm kiếm mỗi lần
            searxng_url: URL của SearXNG server cho web search (optional)
            enable_web_search: Bật web search với SearXNG
            prompt_templates: Custom prompt templates (optional)
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.embedding_model = embedding_model
        self.max_iterations = max_iterations
        self.top_k = top_k
        self.searxng_url = searxng_url
        self.enable_web_search = enable_web_search
        
        # Khởi tạo prompt templates
        self.prompt_templates = prompt_templates or PromptTemplates()
        
        # Khởi tạo các components
        self.legal_search: Optional[LegalSearch] = None
        self.web_search: Optional[LegalWebSearch] = None
        self.llm: Optional[ChatOllama] = None
        self.workflow: Optional[StateGraph] = None
        
    def initialize(self) -> None:
        """Khởi tạo các components và build workflow."""
        print("Đang khởi tạo LegalRAGAgent...")
        
        # Khởi tạo LegalSearch
        self.legal_search = LegalSearch(
            qdrant_url=self.qdrant_url,
            collection_name=self.collection_name,
            model_name=self.embedding_model
        )
        self.legal_search.initialize()
        self.legal_search.initialize_llm(
            ollama_url=self.ollama_url,
            model_name=self.ollama_model,
            prompt_templates=self.prompt_templates
        )
        
        # Khởi tạo LLM cho agent
        self.llm = ChatOllama(
            base_url=self.ollama_url,
            model=self.ollama_model,
            temperature=0.3
        )
        
        # Khởi tạo web search nếu được bật
        if self.enable_web_search:
            if not WEB_SEARCH_AVAILABLE:
                print("⚠️  Web search disabled: web_search module không khả dụng")
                self.enable_web_search = False
            else:
                try:
                    self.web_search = LegalWebSearch(searxng_url=self.searxng_url)
                    print("✓ Đã khởi tạo SearXNG Web Search")
                except Exception as e:
                    print(f"⚠️  Web search disabled: {e}")
                    self.enable_web_search = False
        
        # Build workflow
        self._build_workflow()
        
        print("✓ Đã khởi tạo LegalRAGAgent thành công!")
    
    def _build_workflow(self) -> None:
        """Build LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Thêm các nodes
        workflow.add_node("decide_action", self._decide_action)
        workflow.add_node("refine_query", self._refine_query)
        workflow.add_node("search", self._search)
        workflow.add_node("search_web", self._search_web)  # NEW: Web search node
        workflow.add_node("generate_answer", self._generate_answer)
        
        # Set entry point
        workflow.set_entry_point("decide_action")
        
        # Thêm edges
        workflow.add_conditional_edges(
            "decide_action",
            self._route_after_decide,
            {
                "refine": "refine_query",
                "search": "search",
                "web_search": "search_web",  # NEW: Route to web search
                "answer": "generate_answer",
                "end": END
            }
        )
        
        workflow.add_edge("refine_query", "search")
        
        # Routes after internal search
        workflow.add_conditional_edges(
            "search",
            self._route_after_search,
            {
                "continue": "decide_action",
                "answer": "generate_answer",
                "end": END
            }
        )
        
        # Routes after web search
        workflow.add_conditional_edges(
            "search_web",
            self._route_after_search,
            {
                "continue": "decide_action",
                "answer": "generate_answer",
                "end": END
            }
        )
        
        workflow.add_edge("generate_answer", END)
        
        self.workflow = workflow.compile()
    
    def _decide_action(self, state: AgentState) -> AgentState:
        """
        Node quyết định hành động tiếp theo.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        question = state["question"]
        query = state.get("query", question)
        iteration = state.get("iteration", 0)
        search_results = state.get("search_results", [])
        web_results = state.get("web_results", [])
        
        # Nếu đã có đủ kết quả hoặc đã lặp quá nhiều lần
        if iteration >= state.get("max_iterations", self.max_iterations):
            state["should_continue"] = False
            return state
        
        # Nếu chưa có kết quả nào, cần search
        if not search_results and not web_results:
            state["should_continue"] = True
            state["needs_refinement"] = False
            state["use_web_search"] = False
            return state
        
        # IMPROVED: Fallback mechanism - nếu đã search nội bộ 2 lần mà câu hỏi về số liệu cụ thể
        # và chưa có web results, tự động trigger web search
        if (self.enable_web_search and 
            iteration >= 2 and 
            not web_results and 
            _contains_specific_data_query(question)):
            print(f"[Quyết định] Fallback: Đã search nội bộ {iteration} lần, câu hỏi về số liệu cụ thể → trigger web_search")
            state["needs_refinement"] = False
            state["should_continue"] = True
            state["use_web_search"] = True
            return state
        
        # Tạo preview của kết quả tìm kiếm
        results_preview = []
        for i, result in enumerate(search_results[:5], 1):
            metadata = result.get("metadata", {})
            text = result.get("text", "")
            article_id = metadata.get("article_id", metadata.get("article", "N/A"))
            preview = f"{i}. [Nội bộ] {article_id}: {text[:100]}..."
            results_preview.append(preview)
        
        for i, result in enumerate(web_results[:3], len(search_results) + 1):
            title = result.get("title", "N/A")
            content = result.get("content", "")
            preview = f"{i}. [Web] {title}: {content[:100]}..."
            results_preview.append(preview)
        
        results_text = "\n".join(results_preview)
        
        # Sử dụng prompt template
        decision_prompt = self.prompt_templates.get_decision_prompt(
            question=question,
            query=query,
            num_internal_results=len(search_results),
            num_web_results=len(web_results),
            iteration=iteration,
            results_preview=results_text,
            enable_web_search=self.enable_web_search
        )

        try:
            print(f"\n[Quyết định] Đang phân tích {len(search_results)} kết quả nội bộ + {len(web_results)} kết quả web...")
            messages = [HumanMessage(content=decision_prompt)]
            response = self.llm.invoke(messages)
            decision = response.content.strip().lower()
            
            print(f"[Quyết định] LLM quyết định: {decision}")
            
            if "refine" in decision:
                state["needs_refinement"] = True
                state["should_continue"] = True
                state["use_web_search"] = False
            elif "web" in decision and self.enable_web_search:
                state["needs_refinement"] = False
                state["should_continue"] = True
                state["use_web_search"] = True
            elif "search" in decision:
                state["needs_refinement"] = False
                state["should_continue"] = True
                state["use_web_search"] = False
            else:  # answer
                state["should_continue"] = False
                state["use_web_search"] = False
        except Exception as e:
            print(f"Lỗi khi quyết định: {e}")
            # Fallback: nếu đã có kết quả thì trả lời, nếu không thì search
            if search_results or web_results:
                state["should_continue"] = False
            else:
                state["should_continue"] = True
                state["needs_refinement"] = False
            state["use_web_search"] = False
        
        return state
    
    def _refine_query(self, state: AgentState) -> AgentState:
        """
        Node tinh chỉnh query.
        
        Args:
            state: Current state
            
        Returns:
            Updated state với query đã được refine
        """
        question = state["question"]
        current_query = state.get("query", question)
        search_results = state.get("search_results", [])
        iteration = state.get("iteration", 0)
        
        # Phân tích kết quả hiện tại để xác định thiếu gì
        articles_found = set()
        for result in search_results:
            metadata = result.get("metadata", {})
            article_id = metadata.get("article_id", "")
            if article_id:
                articles_found.add(article_id)
        
        articles_found_str = ', '.join(sorted(articles_found)) if articles_found else 'Chưa có'
        
        # Sử dụng prompt template
        refine_prompt = self.prompt_templates.get_refine_prompt(
            question=question,
            current_query=current_query,
            iteration=iteration,
            articles_found=articles_found_str
        )

        try:
            print(f"\n[Tinh chỉnh] Đang phân tích để tạo query tốt hơn...")
            messages = [HumanMessage(content=refine_prompt)]
            response = self.llm.invoke(messages)
            refined_query = response.content.strip().strip('"').strip("'")
            
            state["query"] = refined_query
            print(f"✓ Query đã được tinh chỉnh: {refined_query}")
        except Exception as e:
            print(f"Lỗi khi refine query: {e}")
            # Fallback: giữ nguyên query cũ
            state["query"] = current_query
        
        return state
    
    def _search(self, state: AgentState) -> AgentState:
        """
        Node thực hiện tìm kiếm.
        
        Args:
            state: Current state
            
        Returns:
            Updated state với kết quả tìm kiếm mới
        """
        query = state.get("query", state["question"])
        iteration = state.get("iteration", 0)
        existing_results = state.get("search_results", [])
        
        print(f"\n[Lần tìm kiếm {iteration + 1}] Đang tìm kiếm: '{query}'")
        
        try:
            # Thực hiện tìm kiếm
            new_results = self.legal_search.search(
                query=query,
                top_k=self.top_k
            )
            
            # DEBUG
            print(f"DEBUG: Existing: {len(existing_results)}, New: {len(new_results)}")
            
            # FIX: Tạo list mới thay vì mutate list cũ để tránh state mutation bug
            if not existing_results:
                merged_results = new_results
            else:
                # Deduplicate based on text content
                existing_texts = {r.get("text", "") for r in existing_results}
                merged_results = existing_results.copy()  # Tạo bản copy
                
                added_count = 0
                for result in new_results:
                    result_text = result.get("text", "")
                    if result_text and result_text not in existing_texts:
                        merged_results.append(result)
                        existing_texts.add(result_text)
                        added_count += 1
                
                print(f"✓ Tìm thấy {len(new_results)} kết quả, thêm {added_count} kết quả mới. Tổng: {len(merged_results)}")
            
            state["search_results"] = merged_results
            state["iteration"] = iteration + 1
            
            if not existing_results:
                print(f"✓ Tìm thấy {len(new_results)} kết quả. Tổng: {len(merged_results)}")
            
        except Exception as e:
            print(f"Lỗi khi tìm kiếm: {e}")
            state["search_results"] = existing_results
        
        return state
    
    def _search_web(self, state: AgentState) -> AgentState:
        """
        Node thực hiện tìm kiếm trên internet.
        
        Args:
            state: Current state
            
        Returns:
            Updated state với kết quả web search
        """
        query = state.get("query", state["question"])
        iteration = state.get("iteration", 0)
        existing_web_results = state.get("web_results", [])
        
        print(f"\n[Lần tìm kiếm web {iteration + 1}] Đang tìm trên internet: '{query}'")
        
        try:
            if not self.web_search or not self.enable_web_search:
                print("✗ Web search không khả dụng")
                return state
            
            # Search with Vietnamese legal focus
            results = self.web_search.search_vietnamese_law(
                query=query,
                max_results=self.top_k
            )
            
            # Add to web_results (avoid duplicates)
            if not existing_web_results:
                merged_web_results = results
            else:
                # Deduplicate based on content
                existing_contents = {r.get("content", "") for r in existing_web_results}
                merged_web_results = existing_web_results.copy()
                
                added_count = 0
                for result in results:
                    content = result.get("content", "")
                    if content and content not in existing_contents:
                        merged_web_results.append(result)
                        existing_contents.add(content)
                        added_count += 1
                
                print(f"✓ Tìm thấy {len(results)} kết quả web, thêm {added_count} kết quả mới. Tổng: {len(merged_web_results)}")
            
            state["web_results"] = merged_web_results
            state["iteration"] = iteration + 1
            
            if not existing_web_results:
                print(f"✓ Tìm thấy {len(results)} kết quả web. Tổng: {len(merged_web_results)}")
            
        except Exception as e:
            print(f"Lỗi khi tìm kiếm web: {e}")
            state["web_results"] = existing_web_results
        
        return state
    
    def _generate_answer(self, state: AgentState) -> AgentState:
        """
        Node tạo câu trả lời cuối cùng.
        
        Args:
            state: Current state
            
        Returns:
            Updated state với câu trả lời
        """
        question = state["question"]
        search_results = state.get("search_results", [])
        web_results = state.get("web_results", [])
        
        # Combine both sources
        all_results = []
        
        # Add internal results (higher priority)
        for r in search_results:
            result_copy = r.copy()
            result_copy["source_type"] = "internal"
            all_results.append(result_copy)
        
        # Add web results with proper formatting
        for r in web_results:
            # Convert web result format to internal format
            if r.get("type") == "article":
                web_result = {
                    "text": f"[Nguồn web: {r.get('title', 'N/A')}]\n{r.get('content', '')}",
                    "metadata": {
                        "source": "web",
                        "url": r.get("url", ""),
                        "title": r.get("title", "")
                    },
                    "score": r.get("score", 0.0),
                    "source_type": "web"
                }
                all_results.append(web_result)
            elif r.get("type") == "answer":
                # SearXNG summary (if available)
                web_result = {
                    "text": f"[Tóm tắt từ Web Search]\n{r.get('content', '')}",
                    "metadata": {"source": "web_summary"},
                    "score": 1.0,
                    "source_type": "web"
                }
                all_results.append(web_result)
        
        if not all_results:
            state["answer"] = "Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn."
            return state
        
        print(f"\nĐang tạo câu trả lời từ {len(search_results)} kết quả nội bộ + {len(web_results)} kết quả web...")
        
        try:
            # Sử dụng LLM generator để tạo câu trả lời
            answer = self.legal_search.generate_answer(
                question=question,
                results=all_results,
                top_k=len(all_results)
            )
            state["answer"] = answer
            print("✓ Đã tạo câu trả lời")
        except Exception as e:
            print(f"Lỗi khi tạo câu trả lời: {e}")
            state["answer"] = f"Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời: {e}"
        
        return state
    
    def _route_after_decide(self, state: AgentState) -> str:
        """
        Router sau khi decide action.
        
        Args:
            state: Current state
            
        Returns:
            Tên node tiếp theo
        """
        needs_refinement = state.get("needs_refinement", False)
        should_continue = state.get("should_continue", True)
        use_web_search = state.get("use_web_search", False)
        search_results = state.get("search_results", [])
        web_results = state.get("web_results", [])
        
        if not should_continue:
            if search_results or web_results:
                return "answer"
            else:
                return "end"
        
        if needs_refinement:
            return "refine"
        elif use_web_search:
            return "web_search"
        else:
            return "search"
    
    def _route_after_search(self, state: AgentState) -> str:
        """
        Router sau khi search.
        
        Args:
            state: Current state
            
        Returns:
            Tên node tiếp theo
        """
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", self.max_iterations)
        search_results = state.get("search_results", [])
        
        # Nếu đã đạt max iterations, tạo câu trả lời
        if iteration >= max_iterations:
            if search_results:
                return "answer"
            else:
                return "end"
        
        # Nếu không có kết quả nào, kết thúc
        if not search_results:
            return "end"
        
        # Luôn quay lại decide_action để LLM quyết định có cần tìm kiếm thêm
        return "continue"
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Thực hiện query với agentic RAG.
        
        Args:
            question: Câu hỏi của người dùng
            
        Returns:
            Dict chứa answer, search_results và web_results
        """
        if not self.workflow:
            raise ValueError("Agent chưa được khởi tạo. Gọi initialize() trước.")
        
        # Khởi tạo state
        initial_state: AgentState = {
            "question": question,
            "query": question,
            "search_results": [],
            "web_results": [],  # NEW: Initialize web results
            "answer": None,
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "needs_refinement": False,
            "should_continue": True,
            "use_web_search": False  # NEW: Initialize web search flag
        }
        
        # Chạy workflow
        print(f"\n{'='*80}")
        print(f"Câu hỏi: {question}")
        if self.enable_web_search:
            print(f"Web Search: Enabled")
        print(f"{'='*80}\n")
        
        final_state = self.workflow.invoke(initial_state)
        
        return {
            "answer": final_state.get("answer", "Không thể tạo câu trả lời."),
            "search_results": final_state.get("search_results", []),
            "web_results": final_state.get("web_results", []),  # NEW: Return web results
            "iterations": final_state.get("iteration", 0),
            "query_used": final_state.get("query", question)
        }


def main():
    """Hàm main để test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic RAG cho hệ thống pháp lý")
    parser.add_argument(
        "question",
        type=str,
        help="Câu hỏi cần tìm kiếm"
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default="http://localhost:6333",
        help="URL của Qdrant server"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="legal_documents",
        help="Tên collection trong Qdrant"
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://127.0.0.1:11434",
        help="URL của Ollama server"
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="llama3.2",
        help="Tên model Ollama"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Số lần tìm kiếm tối đa"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Số lượng kết quả mỗi lần tìm kiếm"
    )
    
    args = parser.parse_args()
    
    try:
        # Khởi tạo agent
        agent = LegalRAGAgent(
            qdrant_url=args.qdrant_url,
            collection_name=args.collection,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_model,
            max_iterations=args.max_iterations,
            top_k=args.top_k
        )
        agent.initialize()
        
        # Thực hiện query
        result = agent.query(args.question)
        
        # Hiển thị kết quả
        print("\n" + "="*80)
        print("KẾT QUẢ")
        print("="*80)
        print(f"\nCâu trả lời:\n{result['answer']}")
        print(f"\nSố lần tìm kiếm: {result['iterations']}")
        print(f"Query cuối cùng: {result['query_used']}")
        print(f"Số kết quả tìm được: {len(result['search_results'])}")
        
        if result['search_results']:
            print("\nCác điều luật được tham khảo:")
            for i, res in enumerate(result['search_results'][:5], 1):
                metadata = res.get('metadata', {})
                article_id = metadata.get('article_id', metadata.get('article', 'N/A'))
                print(f"  {i}. {article_id}")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

