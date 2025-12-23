"""
Module quản lý prompt templates cho Agentic RAG.
Cho phép customize prompts dễ dàng mà không cần sửa code.
"""

from typing import Dict, Optional, Any


class PromptTemplates:
    """Class quản lý các prompt templates cho hệ thống RAG."""
    
    # Default templates
    DEFAULT_DECISION_PROMPT = """Bạn là một trợ lý pháp lý thông minh. Dựa trên câu hỏi và kết quả tìm kiếm hiện tại, hãy quyết định hành động tiếp theo.

Câu hỏi: {question}
Query hiện tại: {query}
Số kết quả nội bộ: {num_internal_results}
Số kết quả web: {num_web_results}
Số lần đã tìm kiếm: {iteration}

Kết quả tìm kiếm hiện tại:
{results_preview}

PHÂN TÍCH QUAN TRỌNG:
1. Câu hỏi có hỏi về SỐ LIỆU CỤ THỂ (số tiền, tỷ lệ %, mức lương, ngày tháng) không?
2. Kết quả nội bộ có cung cấp CON SỐ CỤ THỂ đó không?
3. Nếu câu hỏi hỏi số cụ thể nhưng kết quả chỉ có khung pháp lý chung → CẦN WEB_SEARCH

Hãy trả lời bằng MỘT TRONG các lựa chọn sau (chỉ trả lời một từ):
- "answer" - Nếu đã có đủ thông tin CỤ THỂ để trả lời câu hỏi
- "refine" - Nếu kết quả không liên quan, cần tinh chỉnh query
- "search" - Nếu cần tìm kiếm thêm trong database nội bộ{web_search_option}

Chỉ trả lời MỘT từ: answer, refine, search{web_search_suffix}."""

    DEFAULT_WEB_SEARCH_GUIDANCE = """
- "web_search" - Nếu câu hỏi về SỐ LIỆU CỤ THỂ (số tiền, tỷ lệ %, ngày tháng) mà kết quả nội bộ KHÔNG có con số cụ thể
  VÍ DỤ: "mức lương tối thiểu vùng 1 là bao nhiêu" → cần web_search vì Bộ luật chỉ nói "theo vùng" nhưng không có số tiền
  VÍ DỤ: "quy định MỚI NHẤT 2024" → cần web_search để tìm nghị định mới
  VÍ DỤ: "tỷ lệ đóng BHXH hiện nay" → cần web_search vì cần số % cụ thể"""

    DEFAULT_REFINE_PROMPT = """Bạn là chuyên gia pháp lý. Hãy trích xuất KHÁI NIỆM PHÁP LÝ chính từ câu hỏi để tìm kiếm trong Bộ luật Lao động.

Câu hỏi gốc: {question}
Query hiện tại: {current_query}
Đã tìm kiếm: {iteration} lần
Các điều đã tìm thấy: {articles_found}

Hãy tạo query TÌM KIẾM MỚI tập trung vào:
1. Khái niệm pháp lý chính (VD: "lương thử việc", "thời gian thử việc", "hợp đồng lao động")
2. Loại bỏ thông tin cụ thể (số tiền, thời gian cụ thể, tên người)
3. Sử dụng thuật ngữ pháp lý chuẩn theo Bộ luật Lao động

Ví dụ:
- "Lương 10 triệu thử việc 2 tháng" → "lương thử việc"
- "Tôi nghỉ việc có được hưởng trợ cấp không" → "trợ cấp thôi việc"

Chỉ trả lời query mới (2-6 từ), KHÔNG giải thích."""

    DEFAULT_SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên nghiệp, chuyên tư vấn Bộ luật Lao động Việt Nam.

QUY TẮC BẮT BUỘC (NGHIÊM NGẶT):
1. CHỈ sử dụng thông tin từ các điều luật được cung cấp bên dưới
2. KHÔNG được tự bịa thêm quy định, tỷ lệ phần trăm, hoặc số liệu không có trong điều luật
3. KHÔNG được nói "theo quy định chung" hoặc "thông thường" nếu không có trong điều luật
4. Nếu thông tin KHÔNG ĐỦ để trả lời đầy đủ câu hỏi, hãy nói rõ: "Các điều luật tìm được chưa đủ thông tin về [vấn đề cụ thể]"
5. LUÔN trích dẫn chính xác số điều và khoản khi đưa ra thông tin
6. Nếu câu hỏi hỏi về con số cụ thể (%, số tiền, số ngày) mà điều luật không nêu rõ, hãy nói: "Điều luật không quy định cụ thể về [vấn đề]"

Trả lời bằng tiếng Việt, rõ ràng, chính xác, trung thực."""

    DEFAULT_USER_PROMPT = """Dựa CHÍNH XÁC và HOÀN TOÀN vào các điều luật sau, hãy trả lời câu hỏi:

{context}

Câu hỏi: {question}

Hãy trả lời theo cấu trúc:
1. Các điều luật liên quan (trích dẫn cụ thể số điều, khoản)
2. Phân tích và trả lời dựa trên nội dung điều luật
3. Lưu ý (nếu thông tin chưa đủ để trả lời đầy đủ câu hỏi)

Nhớ: CHỈ dùng thông tin từ các điều luật trên, KHÔNG bịa thêm."""

    def __init__(self, custom_templates: Optional[Dict[str, str]] = None):
        """
        Khởi tạo PromptTemplates.
        
        Args:
            custom_templates: Dict chứa custom templates để override defaults
                Các key có thể có:
                - "decision_prompt": Template cho quyết định hành động
                - "web_search_guidance": Hướng dẫn về web search
                - "refine_prompt": Template cho refine query
                - "system_prompt": System prompt cho LLM
                - "user_prompt": User prompt cho generate answer
        """
        self.templates = {
            "decision_prompt": self.DEFAULT_DECISION_PROMPT,
            "web_search_guidance": self.DEFAULT_WEB_SEARCH_GUIDANCE,
            "refine_prompt": self.DEFAULT_REFINE_PROMPT,
            "system_prompt": self.DEFAULT_SYSTEM_PROMPT,
            "user_prompt": self.DEFAULT_USER_PROMPT,
        }
        
        # Override với custom templates nếu có
        if custom_templates:
            self.templates.update(custom_templates)
    
    def get_decision_prompt(
        self,
        question: str,
        query: str,
        num_internal_results: int,
        num_web_results: int,
        iteration: int,
        results_preview: str,
        enable_web_search: bool = False
    ) -> str:
        """
        Tạo prompt cho quyết định hành động.
        
        Args:
            question: Câu hỏi gốc
            query: Query hiện tại
            num_internal_results: Số kết quả nội bộ
            num_web_results: Số kết quả web
            iteration: Số lần đã tìm kiếm
            results_preview: Preview của kết quả
            enable_web_search: Có bật web search không
            
        Returns:
            Prompt đã được format
        """
        web_search_option = ""
        web_search_suffix = ""
        
        if enable_web_search:
            web_search_option = self.templates["web_search_guidance"]
            web_search_suffix = ", hoặc web_search"
        
        return self.templates["decision_prompt"].format(
            question=question,
            query=query,
            num_internal_results=num_internal_results,
            num_web_results=num_web_results,
            iteration=iteration,
            results_preview=results_preview,
            web_search_option=web_search_option,
            web_search_suffix=web_search_suffix
        )
    
    def get_refine_prompt(
        self,
        question: str,
        current_query: str,
        iteration: int,
        articles_found: str
    ) -> str:
        """
        Tạo prompt cho refine query.
        
        Args:
            question: Câu hỏi gốc
            current_query: Query hiện tại
            iteration: Số lần đã tìm kiếm
            articles_found: Các điều đã tìm thấy
            
        Returns:
            Prompt đã được format
        """
        return self.templates["refine_prompt"].format(
            question=question,
            current_query=current_query,
            iteration=iteration,
            articles_found=articles_found
        )
    
    def get_system_prompt(self) -> str:
        """
        Lấy system prompt cho LLM.
        
        Returns:
            System prompt
        """
        return self.templates["system_prompt"]
    
    def get_user_prompt(self, context: str, question: str) -> str:
        """
        Tạo user prompt cho generate answer.
        
        Args:
            context: Context từ kết quả tìm kiếm
            question: Câu hỏi của người dùng
            
        Returns:
            User prompt đã được format
        """
        return self.templates["user_prompt"].format(
            context=context,
            question=question
        )
    
    def update_template(self, template_name: str, template_content: str) -> None:
        """
        Cập nhật một template cụ thể.
        
        Args:
            template_name: Tên template cần cập nhật
            template_content: Nội dung mới của template
        """
        if template_name not in self.templates:
            raise ValueError(
                f"Template '{template_name}' không tồn tại. "
                f"Các template có sẵn: {list(self.templates.keys())}"
            )
        self.templates[template_name] = template_content
    
    def get_all_templates(self) -> Dict[str, str]:
        """
        Lấy tất cả templates hiện tại.
        
        Returns:
            Dict chứa tất cả templates
        """
        return self.templates.copy()


# Convenience function để tạo custom templates
def create_custom_templates(**kwargs) -> Dict[str, str]:
    """
    Tạo dict custom templates từ keyword arguments.
    
    Args:
        **kwargs: Các template cần customize
        
    Returns:
        Dict chứa custom templates
        
    Example:
        >>> templates = create_custom_templates(
        ...     system_prompt="Bạn là chuyên gia...",
        ...     decision_prompt="Hãy quyết định..."
        ... )
    """
    return kwargs
