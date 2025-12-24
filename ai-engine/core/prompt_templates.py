"""
Module quản lý prompt templates cho Agentic RAG.
Cho phép customize prompts dễ dàng mà không cần sửa code.
"""

from typing import Dict, Optional, Any
from datetime import datetime


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
1. Câu hỏi có hỏi về SỐ LIỆU CỤ THỂ (tiền, %, ngày...), ĐỊA CHỈ, hay THỦ TỤC hành chính thực tế không?
2. Kết quả nội bộ có cung cấp thông tin CHI TIẾT đó không?
3. Nếu kết quả nội bộ chỉ có quy định chung (khung luật) nhưng người dùng hỏi thông tin thực tế (con số, địa chỉ, quy trình nộp) → BẮT BUỘC chọn "web_search".
4. Nếu database nội bộ trả về kết quả không liên quan → chọn "refine" hoặc "web_search".

Hãy trả lời bằng MỘT TRONG các lựa chọn sau (chỉ trả lời một từ):
- "answer" - Nếu đã có đủ thông tin CỤ THỂ để trả lời câu hỏi
- "refine" - Nếu kết quả không liên quan, cần tinh chỉnh query
- "search" - Nếu cần tìm kiếm thêm trong database nội bộ{web_search_option}

Chỉ trả lời MỘT từ: answer, refine, search{web_search_suffix}."""

    DEFAULT_WEB_SEARCH_GUIDANCE = """
- "web_search" CHỈ được chọn khi:
  1. Câu hỏi về SỐ LIỆU CỤ THỂ biến động (lương tối thiểu, lãi suất, tỷ lệ BHXH {current_year}).
  2. Câu hỏi về ĐỊA ĐIỂM thực tế (địa chỉ cơ quan, văn phòng, nơi nộp hồ sơ, số điện thoại).
  3. Câu hỏi về THỦ TỤC hành chính thực tế (mẫu đơn, quy trình online/offline).
  4. Câu hỏi về TIN TỨC/SỰ KIỆN mới nhất xảy ra trong năm {current_year} hoặc gần đây.
  5. Nội dung trong database nội bộ (nếu có) đã QUÁ CŨ hoặc KHÔNG ĐỦ chi tiết thực tế.
  
  LƯU Ý QUAN TRỌNG:
  - Nếu kết quả nội bộ chỉ có "quy định chung" mà không có "con số/địa chỉ cụ thể", BẮT BUỘC phải web_search.
  - Với câu hỏi địa điểm (ví dụ: "ở Quận 1"), cần tìm chính xác địa chỉ tại khu vực đó. Nếu không có, tìm địa điểm GẦN NHẤT."""

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

    DEFAULT_SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên nghiệp, chuyên tư vấn pháp luật Việt Nam.
Hôm nay là: {current_date} (Năm {current_year}).

QUY TẮC BẮT BUỘC (NGHIÊM NGẶT):
1. ƯU TIÊN SỐ 1: Sử dụng thông tin từ các điều luật nội bộ được cung cấp.
2. ƯU TIÊN SỐ 2: Sử dụng thông tin từ kết quả Web Search (nếu có) để bổ sung các số liệu thực tế, mức lương, địa chỉ, hoặc quy định mới nhất chưa có trong dữ liệu nội bộ.
3. KHI TRẢ LỜI VỀ ĐỊA ĐIỂM/THỦ TỤC:
   - Phải cung cấp ĐỊA CHỈ CỤ THỂ, CHÍNH XÁC (số nhà, đường, phường, quận) nếu tìm thấy.
   - Nếu không tìm thấy địa chỉ chính xác tại quận/huyện người dùng hỏi, hãy gợi ý địa chỉ GẦN NHẤT.
   - Đừng trả lời chung chung kiểu "nộp tại trung tâm dịch vụ việc làm" mà không đưa ra địa chỉ ví dụ.
4. TRÍCH DẪN RÕ RÀNG:
   - Với thông tin từ luật: "Theo Điều X, Bộ luật Lao động..."
   - Với thông tin từ Web: "Theo thông tin từ [Nguồn Web]..."
   - Với thông tin tổng hợp: Kết hợp cả hai để có câu trả lời đầy đủ nhất.
5. Nếu thông tin hoàn toàn KHÔNG CÓ trong cả luật lẫn web, hãy trung thực nhận lỗi.

Trả lời bằng tiếng Việt, rõ ràng, chính xác, trung thực, LUÔN CẬP NHẬT theo thời điểm hiện tại ({current_year})."""

    DEFAULT_USER_PROMPT = """Dựa CHÍNH XÁC và HOÀN TOÀN vào các điều luật sau, hãy trả lời câu hỏi:

{context}

Câu hỏi: {question}

Hãy trả lời theo cấu trúc:
1. Các điều luật liên quan (trích dẫn cụ thể số điều, khoản)
2. Phân tích và trả lời dựa trên nội dung điều luật
3. Lưu ý (nếu thông tin chưa đủ để trả lời đầy đủ câu hỏi)

Nhớ: CHỈ dùng thông tin từ các điều luật trên, KHÔNG bịa thêm."""

    DEFAULT_ROUTER_PROMPT = """Bạn là một bộ phân loại câu hỏi pháp lý thông minh. Nhiệm vụ của bạn là xác định loại thông tin mà người dùng đang tìm kiếm.

Câu hỏi: {question}

Hãy phân loại vào một trong hai nhóm sau:
1. "INTERNAL": Nếu câu hỏi về LÝ THUYẾT, ĐỊNH NGHĨA, NGUYÊN TẮC, hoặc CÁC QUY ĐỊNH CHUNG trong Bộ luật (Ví dụ: "thử việc tối đa bao lâu", "nguyên tắc sa thải", "hợp đồng lao động là gì").
2. "EXTERNAL": Nếu câu hỏi cần SỐ LIỆU CỤ THỂ, BIẾN ĐỘNG THEO THỜI GIAN, TIN TỨC, ĐỊA CHỈ, THỦ TỤC THỰC TẾ hoặc LIÊN HỆ (Ví dụ: "lương tối thiểu vùng 1 năm nay", "địa chỉ bảo hiểm xã hội quận 3", "mẫu đơn xin nghỉ việc", "lãi suất chậm đóng BHXH").

Chỉ trả lời đúng một từ: INTERNAL hoặc EXTERNAL."""

    def __init__(self, custom_templates: Optional[Dict[str, str]] = None):
        """
        Khởi tạo PromptTemplates.
        
        Args:
            custom_templates: Dict chứa custom templates để override defaults
        """
        self.templates = {
            "decision_prompt": self.DEFAULT_DECISION_PROMPT,
            "web_search_guidance": self.DEFAULT_WEB_SEARCH_GUIDANCE,
            "refine_prompt": self.DEFAULT_REFINE_PROMPT,
            "system_prompt": self.DEFAULT_SYSTEM_PROMPT,
            "user_prompt": self.DEFAULT_USER_PROMPT,
            "router_prompt": self.DEFAULT_ROUTER_PROMPT,
        }
        
        # Override với custom templates nếu có
        if custom_templates:
            self.templates.update(custom_templates)
            
    def get_router_prompt(self, question: str) -> str:
        """
        Tạo prompt cho router phân loại câu hỏi.
        
        Args:
            question: Câu hỏi của người dùng
            
        Returns:
            Prompt đã được format
        """
        return self.templates["router_prompt"].format(question=question)
    
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
        
        if not current_year:
            from datetime import datetime
            current_year = str(datetime.now().year)

        print(f"[Prompt] Sử dụng năm: {current_year}")
        
        web_search_option = ""
        web_search_suffix = ""
        
        if enable_web_search:
            web_search_option = self.templates["web_search_guidance"].format(current_year=current_year)
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
    
    def get_system_prompt(self, current_date: str = "", current_year: str = "") -> str:
        """
        Tạo system prompt.
        
        Args:
            current_date: Ngày hiện tại (DD/MM/YYYY)
            current_year: Năm hiện tại (YYYY)
            
        Returns:
            System prompt
        """
        # Fallback values if empty
        if not current_date:
            from datetime import datetime
            now = datetime.now()
            current_date = now.strftime("%d/%m/%Y")
            current_year = str(now.year)
            
        return self.templates["system_prompt"].format(
            current_date=current_date,
            current_year=current_year
        )
    
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
