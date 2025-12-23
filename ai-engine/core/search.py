"""
Module để tìm kiếm các điều luật liên quan từ câu hỏi của người dùng.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Thêm thư mục ai-engine vào path để import
current_file = Path(__file__).resolve()
ai_engine_dir = current_file.parent.parent
sys.path.insert(0, str(ai_engine_dir))

# Import modules
from embedding.embedder import VietnameseEmbedder
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Import LLM generator
try:
    from .llm_generator import OllamaGenerator
except ImportError:
    # Fallback nếu chạy trực tiếp
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from llm_generator import OllamaGenerator


class LegalSearch:
    """Class để tìm kiếm các điều luật liên quan."""
    
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "legal_documents",
        model_name: str = "bkai-foundation-models/vietnamese-bi-encoder"
    ):
        """
        Khởi tạo LegalSearch.
        
        Args:
            qdrant_url: URL của Qdrant server
            collection_name: Tên collection trong Qdrant
            model_name: Tên model để embed câu hỏi
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.model_name = model_name
        
        self.embedder: Optional[VietnameseEmbedder] = None
        self.client: Optional[QdrantClient] = None
        self.llm_generator: Optional[OllamaGenerator] = None
    
    def initialize(self) -> None:
        """Khởi tạo embedder và kết nối Qdrant."""
        # Load embedder
        print(f"Đang load model: {self.model_name}")
        self.embedder = VietnameseEmbedder(self.model_name)
        self.embedder.load_model()
        
        # Kết nối Qdrant
        print(f"Đang kết nối với Qdrant tại: {self.qdrant_url}")
        self.client = QdrantClient(url=self.qdrant_url)
        
        # Kiểm tra collection có tồn tại không
        collections = self.client.get_collections()
        collection_exists = any(
            col.name == self.collection_name 
            for col in collections.collections
        )
        
        if not collection_exists:
            raise ValueError(f"Collection '{self.collection_name}' không tồn tại trong Qdrant!")
        
        print(f"Đã kết nối thành công với collection: {self.collection_name}")
    
    def search(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các điều luật liên quan với câu hỏi.
        
        Args:
            query: Câu hỏi của người dùng
            top_k: Số lượng kết quả trả về (mặc định 3)
            score_threshold: Ngưỡng điểm tối thiểu (None = không giới hạn)
            
        Returns:
            List các dict chứa thông tin điều luật liên quan:
            {
                "score": float,
                "text": str,
                "metadata": Dict[str, Any]
            }
        """
        if not self.embedder or not self.client:
            raise ValueError("Chưa khởi tạo. Gọi initialize() trước.")
        
        # Embed câu hỏi
        print(f"\nĐang embed câu hỏi: '{query}'")
        query_embedding = self.embedder.encode_single(query)
        
        # Search trong Qdrant
        print(f"Đang tìm kiếm top {top_k} kết quả...")
        
        query_vector = query_embedding.tolist()
        
        # Dùng query_points với vector trực tiếp (API mới)
        # query_points có thể nhận vector trực tiếp hoặc NamedVector
        query_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )
        
        search_results = query_result.points
        
        # Format kết quả
        results = []
        for point in search_results:
            # point có thể là ScoredPoint hoặc PointStruct
            score = getattr(point, 'score', 0.0)
            payload = getattr(point, 'payload', {}) or {}
            
            results.append({
                "score": score,
                "text": payload.get("text", ""),
                "metadata": {
                    k: v for k, v in payload.items() 
                    if k != "text"
                }
            })
        
        return results
    
    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        article_id: Optional[str] = None,
        chapter: Optional[str] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm với filter theo metadata.
        
        Args:
            query: Câu hỏi của người dùng
            top_k: Số lượng kết quả trả về
            article_id: Filter theo article_id (ví dụ: "Dieu_5")
            chapter: Filter theo chapter (ví dụ: "Chương I")
            score_threshold: Ngưỡng điểm tối thiểu
            
        Returns:
            List các dict chứa thông tin điều luật liên quan
        """
        if not self.embedder or not self.client:
            raise ValueError("Chưa khởi tạo. Gọi initialize() trước.")
        
        # Embed câu hỏi
        query_embedding = self.embedder.encode_single(query)
        
        # Tạo filter nếu có
        query_filter = None
        if article_id or chapter:
            conditions = []
            if article_id:
                conditions.append(
                    FieldCondition(
                        key="article_id",
                        match=MatchValue(value=article_id)
                    )
                )
            if chapter:
                conditions.append(
                    FieldCondition(
                        key="chapter",
                        match=MatchValue(value=chapter)
                    )
                )
            
            if conditions:
                query_filter = Filter(must=conditions)
        
        # Search trong Qdrant với filter
        query_vector = query_embedding.tolist()
        
        # Query points với vector và filter
        query_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold
        )
        
        search_results = query_result.points
        
        # Format kết quả
        results = []
        for point in search_results:
            # point có thể là ScoredPoint hoặc PointStruct
            score = getattr(point, 'score', 0.0)
            payload = getattr(point, 'payload', {}) or {}
            
            results.append({
                "score": score,
                "text": payload.get("text", ""),
                "metadata": {
                    k: v for k, v in payload.items() 
                    if k != "text"
                }
            })
        
        return results
    
    def initialize_llm(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        model_name: str = "llama3.2",
        prompt_templates = None
    ) -> None:
        """
        Khởi tạo LLM generator (Ollama).
        
        Args:
            ollama_url: URL của Ollama server
            model_name: Tên model Ollama
            prompt_templates: Custom prompt templates (optional)
        """
        self.llm_generator = OllamaGenerator(
            base_url=ollama_url,
            model_name=model_name,
            prompt_templates=prompt_templates
        )
        
        # Kiểm tra kết nối
        if not self.llm_generator.check_connection():
            raise ConnectionError(
                f"Không thể kết nối với Ollama tại {ollama_url}.\n"
                "Hãy đảm bảo Ollama đang chạy."
            )
        
        # Kiểm tra model
        if not self.llm_generator.check_model():
            print(f"\n⚠️  Model '{model_name}' chưa có sẵn.")
            print(f"Đang tự động pull model '{model_name}'...")
            print("Quá trình này có thể mất vài phút tùy thuộc vào kích thước model...")
            
            # Tự động pull model
            if self._pull_model(model_name):
                print(f"✓ Đã pull model '{model_name}' thành công!")
            else:
                raise ValueError(
                    f"Không thể pull model '{model_name}'.\n"
                    f"Hãy thử pull thủ công bằng lệnh: curl http://127.0.0.1:11434/api/pull -d '{{\"name\": \"{model_name}\"}}'"
                )
        else:
            print(f"✓ Model '{model_name}' đã có sẵn.")
        
        print(f"Đã khởi tạo Ollama với model: {model_name}")
    
    def _pull_model(self, model_name: str) -> bool:
        """
        Pull model từ Ollama server.
        
        Args:
            model_name: Tên model cần pull
            
        Returns:
            True nếu thành công, False nếu không
        """
        import json
        import requests
        
        url = f"{self.llm_generator.base_url}/api/pull"
        payload = {"name": model_name}
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=None)
            response.raise_for_status()
            
            # Stream response để hiển thị progress
            for line in response.iter_lines():
                if line:
                    try:
                        data = line.decode('utf-8')
                        # Parse JSON lines
                        for json_line in data.split('\n'):
                            if json_line.strip():
                                try:
                                    result = json.loads(json_line)
                                    if 'status' in result:
                                        status = result['status']
                                        if 'downloading' in status.lower() or 'pulling' in status.lower():
                                            print(f"  {status}")
                                        elif 'complete' in status.lower() or 'success' in status.lower():
                                            print(f"  {status}")
                                except:
                                    pass
                    except:
                        pass
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Lỗi khi pull model: {e}")
            return False
    
    def generate_answer(
        self,
        question: str,
        results: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 3
    ) -> str:
        """
        Tìm kiếm và generate câu trả lời tự nhiên.
        
        Args:
            question: Câu hỏi của người dùng
            results: Kết quả tìm kiếm (nếu None sẽ tự động search)
            top_k: Số lượng kết quả để dùng làm context
            
        Returns:
            Câu trả lời được generate
        """
        if not self.llm_generator:
            raise ValueError("LLM chưa được khởi tạo. Gọi initialize_llm() trước.")
        
        # Nếu chưa có results, tự động search
        if results is None:
            results = self.search(question, top_k=top_k)
        
        # Generate answer
        print("\nĐang tạo câu trả lời với LLM...")
        answer = self.llm_generator.generate_answer(question, results)
        
        return answer
    
    def display_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Hiển thị kết quả tìm kiếm ra màn hình.
        
        Args:
            results: List các kết quả từ search()
        """
        if not results:
            print("\nKhông tìm thấy kết quả nào.")
            return
        
        print("\n" + "="*80)
        print(f"Tìm thấy {len(results)} điều luật liên quan:")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            score = result['score']
            metadata = result['metadata']
            text = result['text']
            
            print(f"\n[{i}] Điểm tương đồng: {score:.4f}")
            print("-" * 80)
            
            # Hiển thị metadata
            if metadata.get('article_id'):
                print(f"Điều: {metadata['article_id']}")
            if metadata.get('article_title'):
                print(f"Tiêu đề: {metadata['article_title']}")
            if metadata.get('clause_id'):
                print(f"Khoản: {metadata['clause_id']}")
            if metadata.get('chapter'):
                print(f"Chương: {metadata['chapter']}")
                if metadata.get('chapter_title'):
                    print(f"  - {metadata['chapter_title']}")
            if metadata.get('section'):
                print(f"Mục: {metadata['section']}")
                if metadata.get('section_title'):
                    print(f"  - {metadata['section_title']}")
            
            print("\nNội dung:")
            # Hiển thị text (giới hạn độ dài nếu quá dài)
            if len(text) > 500:
                print(text[:500] + "...")
            else:
                print(text)
            
            print("-" * 80)


def main():
    """Hàm main để test và chạy thử."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tìm kiếm điều luật liên quan")
    parser.add_argument(
        "query",
        type=str,
        help="Câu hỏi cần tìm kiếm"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Số lượng kết quả trả về (mặc định: 3)"
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
        "--score-threshold",
        type=float,
        default=None,
        help="Ngưỡng điểm tối thiểu (0.0 - 1.0)"
    )
    parser.add_argument(
        "--generate-answer",
        action="store_true",
        help="Generate câu trả lời tự nhiên bằng LLM (Ollama)"
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
        help="Tên model Ollama để sử dụng"
    )
    
    args = parser.parse_args()
    
    try:
        # Khởi tạo searcher
        searcher = LegalSearch(
            qdrant_url=args.qdrant_url,
            collection_name=args.collection
        )
        searcher.initialize()
        
        # Tìm kiếm
        results = searcher.search(
            query=args.query,
            top_k=args.top_k,
            score_threshold=args.score_threshold
        )
        
        # Hiển thị kết quả
        searcher.display_results(results)
        
        # Generate answer nếu được yêu cầu
        if args.generate_answer:
            print("\n" + "="*80)
            print("ĐANG TẠO CÂU TRẢ LỜI TỰ NHIÊN...")
            print("="*80)
            
            searcher.initialize_llm(
                ollama_url=args.ollama_url,
                model_name=args.ollama_model
            )
            
            answer = searcher.generate_answer(args.query, results)
            
            print("\n" + "="*80)
            print("CÂU TRẢ LỜI:")
            print("="*80)
            print(answer)
            print("="*80)
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

