"""
Module để tạo câu trả lời tự nhiên từ kết quả tìm kiếm sử dụng Ollama.
"""

import requests
from typing import List, Dict, Any, Optional
import json

# Import PromptTemplates if available
try:
    from core.prompt_templates import PromptTemplates
except ImportError:
    try:
        from prompt_templates import PromptTemplates
    except ImportError:
        PromptTemplates = None


class OllamaGenerator:
    """Class để generate câu trả lời từ Ollama LLM."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model_name: str = "qwen2.5:7b",  # Có thể dùng "qwen2.5:7b", "llama3.2", "mistral", "phi3", etc.
        prompt_templates: Optional['PromptTemplates'] = None
    ):
        """
        Khởi tạo OllamaGenerator.
        
        Args:
            base_url: URL của Ollama server
            model_name: Tên model Ollama để sử dụng
            prompt_templates: Custom prompt templates (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.api_url = f"{self.base_url}/api/generate"
        self.prompt_templates = prompt_templates
    
    def check_connection(self) -> bool:
        """
        Kiểm tra kết nối với Ollama server.
        
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            # Thử với 127.0.0.1 nếu localhost không hoạt động
            if "localhost" in self.base_url:
                try:
                    alt_url = self.base_url.replace("localhost", "127.0.0.1")
                    response = requests.get(f"{alt_url}/api/tags", timeout=10)
                    if response.status_code == 200:
                        self.base_url = alt_url
                        self.api_url = f"{self.base_url}/api/generate"
                        return True
                except:
                    pass
            return False
        except Exception:
            return False
    
    def check_model(self) -> bool:
        """
        Kiểm tra xem model có sẵn không.
        
        Returns:
            True nếu model có sẵn, False nếu không
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model['name'].startswith(self.model_name) for model in models)
            return False
        except Exception:
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate câu trả lời từ prompt.
        
        Args:
            prompt: Prompt để generate
            system_prompt: System prompt (optional)
            temperature: Temperature cho generation (0.0 - 1.0)
            max_tokens: Số token tối đa
            
        Returns:
            Câu trả lời được generate
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Không thể kết nối với Ollama: {e}")
        except Exception as e:
            raise ValueError(f"Lỗi khi generate: {e}")
    
    def generate_answer(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        language: str = "vi"
    ) -> str:
        """
        Generate câu trả lời từ câu hỏi và kết quả tìm kiếm.
        
        Args:
            question: Câu hỏi của người dùng
            search_results: List các kết quả tìm kiếm từ Qdrant
            language: Ngôn ngữ trả lời (mặc định: tiếng Việt)
            
        Returns:
            Câu trả lời được generate
        """
        # Tạo context từ search results
        context_parts = []
        for i, result in enumerate(search_results, 1):
            metadata = result.get('metadata', {})
            text = result.get('text', '')
            
            context_item = f"[Điều luật {i}]\n"
            if metadata.get('article_id'):
                context_item += f"Điều: {metadata['article_id']}\n"
            if metadata.get('article_title'):
                context_item += f"Tiêu đề: {metadata['article_title']}\n"
            if metadata.get('clause_id'):
                context_item += f"Khoản: {metadata['clause_id']}\n"
            
            context_item += f"Nội dung: {text}\n"
            context_parts.append(context_item)
        
        context = "\n".join(context_parts)
        
        # Use prompt templates if available, otherwise use default
        if self.prompt_templates:
            system_prompt = self.prompt_templates.get_system_prompt()
            user_prompt = self.prompt_templates.get_user_prompt(
                context=context,
                question=question
            )
        else:
            # Fallback to default prompts
            system_prompt = """Bạn là trợ lý pháp lý chuyên nghiệp, chuyên tư vấn Bộ luật Lao động Việt Nam.

QUY TẮC BẮT BUỘC (NGHIÊM NGẶT):
1. CHỈ sử dụng thông tin từ các điều luật được cung cấp bên dưới
2. KHÔNG được tự bịa thêm quy định, tỷ lệ phần trăm, hoặc số liệu không có trong điều luật
3. KHÔNG được nói "theo quy định chung" hoặc "thông thường" nếu không có trong điều luật
4. Nếu thông tin KHÔNG ĐỦ để trả lời đầy đủ câu hỏi, hãy nói rõ: "Các điều luật tìm được chưa đủ thông tin về [vấn đề cụ thể]"
5. LUÔN trích dẫn chính xác số điều và khoản khi đưa ra thông tin
6. Nếu câu hỏi hỏi về con số cụ thể (%, số tiền, số ngày) mà điều luật không nêu rõ, hãy nói: "Điều luật không quy định cụ thể về [vấn đề]"

Trả lời bằng tiếng Việt, rõ ràng, chính xác, trung thực."""

            user_prompt = f"""Dựa CHÍNH XÁC và HOÀN TOÀN vào các điều luật sau, hãy trả lời câu hỏi:

{context}

Câu hỏi: {question}

Hãy trả lời theo cấu trúc:
1. Các điều luật liên quan (trích dẫn cụ thể số điều, khoản)
2. Phân tích và trả lời dựa trên nội dung điều luật
3. Lưu ý (nếu thông tin chưa đủ để trả lời đầy đủ câu hỏi)

Nhớ: CHỈ dùng thông tin từ các điều luật trên, KHÔNG bịa thêm."""

        # Generate answer with strict grounding
        answer = self.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Giảm xuống 0.1 để chính xác hơn, ít hallucination
            max_tokens=2000
        )
        
        return answer


def main():
    """Test function."""
    generator = OllamaGenerator(model_name="qwen2.5:7b")
    
    if not generator.check_connection():
        print("Không thể kết nối với Ollama server!")
        print("Hãy đảm bảo Ollama đang chạy tại http://localhost:11434")
        return
    
    if not generator.check_model():
        print(f"Model '{generator.model_name}' không có sẵn!")
        print("Hãy pull model bằng lệnh: ollama pull qwen2.5:7b")
        return
    
    # Test với sample data
    question = "Thử việc tối đa bao nhiêu ngày?"
    search_results = [
        {
            "score": 0.41,
            "text": "Bộ luật Lao động. Điều 25. Thời gian thử việc...",
            "metadata": {
                "article_id": "Dieu_25",
                "article_title": "Thời gian thử việc",
                "clause_id": "Khoan_2"
            }
        }
    ]
    
    print("Đang generate câu trả lời...")
    answer = generator.generate_answer(question, search_results)
    print("\nCâu trả lời:")
    print(answer)


if __name__ == "__main__":
    main()

