"""
Module để chunk các điều khoản thành các phần nhỏ hơn dựa trên các khoản (clauses).
Áp dụng logic phân tích để quyết định có nên tách hay giữ nguyên.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class ArticleChunker:
    """Class để chunk các điều khoản thành các phần nhỏ hơn."""
    
    # Pattern để tìm các khoản: "1.", "2.", "Khoản 1", "Khoản 2", ...
    # Tìm pattern số + dấu chấm hoặc dấu hai chấm
    CLAUSE_PATTERN = re.compile(
        r'\b(\d+)[\.:]\s+',
        re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern để tìm các mục con: "a)", "b)", "c)", ...
    SUB_ITEM_PATTERN = re.compile(
        r'[a-zđ\)\)]\s*\)\s*',
        re.IGNORECASE
    )
    
    def __init__(self, articles_json_path: str):
        """
        Khởi tạo ArticleChunker.
        
        Args:
            articles_json_path: Đường dẫn đến file JSON chứa các điều khoản
        """
        self.articles_json_path = Path(articles_json_path)
        if not self.articles_json_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {articles_json_path}")
        
        self.articles: List[Dict[str, Any]] = []
        self.chunks: List[Dict[str, Any]] = []
    
    def load_articles(self) -> None:
        """Đọc các điều khoản từ file JSON."""
        with open(self.articles_json_path, 'r', encoding='utf-8') as f:
            self.articles = json.load(f)
        print(f"Đã load {len(self.articles)} điều khoản")
    
    def _extract_clauses(self, content: str) -> List[Tuple[int, int, str]]:
        """
        Trích xuất các khoản từ nội dung điều khoản.
        
        Args:
            content: Nội dung điều khoản
            
        Returns:
            List các tuple (clause_number, start_pos, clause_text)
        """
        clauses = []
        
        # Loại bỏ phần trùng lặp trong text (có thể có "Điều X. ... Điều X. ...")
        # Tìm vị trí bắt đầu của nội dung thực sự
        content_cleaned = content
        
        # Tìm tất cả các pattern số + dấu chấm
        matches = []
        for match in self.CLAUSE_PATTERN.finditer(content_cleaned):
            pos = match.start()
            clause_number = int(match.group(1))
            
            # Lấy context xung quanh để kiểm tra
            context_before = content_cleaned[max(0, pos-30):pos]
            context_after = content_cleaned[pos:min(len(content_cleaned), pos+50)]
            
            # Bỏ qua nếu là số trong "Điều X", "Chương X", "Mục X", hoặc "Khoản X"
            context_before_lower = context_before.lower()
            if any(keyword in context_before_lower[-15:] for keyword in ['điều', 'chương', 'mục', 'khoản']):
                continue
            
            # Bỏ qua nếu số quá lớn (thường khoản chỉ từ 1-20)
            if clause_number > 20:
                continue
            
            # Kiểm tra xem có phải là khoản hợp lệ
            # Khoản thường có format: "1. Người..." hoặc "2. Người..." hoặc "1. Bảo đảm..."
            # Sau số + dấu chấm phải có chữ cái hoặc từ tiếng Việt, và thường là chữ hoa
            after_match = re.match(r'\d+[\.:]\s+([A-Za-zĐẠ-ỹ])', context_after)
            if not after_match:
                continue
            
            # Kiểm tra xem có phải là khoản độc lập
            # Khoản thường bắt đầu bằng chữ hoa sau dấu chấm và có ít nhất 1 từ đầy đủ
            first_char_after = after_match.group(1)
            
            # Lấy 20 ký tự sau để kiểm tra xem có từ đầy đủ không
            text_after = context_after[:20].strip()
            # Kiểm tra xem có từ đầy đủ (ít nhất 3 ký tự) sau số
            if len(text_after) < 5:
                continue
            
            # Chỉ chấp nhận nếu bắt đầu bằng chữ hoa (khoản thường bắt đầu bằng chữ hoa)
            if first_char_after.isupper() or first_char_after in 'ĐẠ-ỹ':
                # Kiểm tra thêm: không phải là số trong "áp dụng 1" hoặc tương tự
                # Khoản hợp lệ thường có dấu chấm hoặc dấu hai chấm và khoảng trắng sau số
                if re.match(r'\d+[\.:]\s+[A-Z]', text_after):
                    matches.append((clause_number, pos, match))
        
        # Sắp xếp theo vị trí
        matches.sort(key=lambda x: x[1])
        
        # Lọc các khoản hợp lệ (loại bỏ các khoản trùng lặp hoặc không hợp lệ)
        valid_clauses = []
        for i, (clause_number, start_pos, match) in enumerate(matches):
            # Vị trí kết thúc là vị trí bắt đầu của khoản tiếp theo, hoặc cuối nội dung
            if i + 1 < len(matches):
                end_pos = matches[i + 1][1]
            else:
                end_pos = len(content_cleaned)
            
            clause_text = content_cleaned[start_pos:end_pos].strip()
            
            # Chỉ thêm nếu clause_text có nội dung đáng kể (ít nhất 20 ký tự)
            if len(clause_text) >= 20:
                # Kiểm tra xem có phải là khoản thực sự
                # Khoản thường bắt đầu bằng số + dấu chấm + chữ hoa + từ
                if re.match(r'^\d+[\.:]\s+[A-ZĐẠ-ỹ]', clause_text):
                    valid_clauses.append((clause_number, start_pos, clause_text))
        
        return valid_clauses
    
    def _count_sub_items(self, text: str) -> int:
        """
        Đếm số lượng mục con (a, b, c, ...) trong text.
        
        Args:
            text: Văn bản cần đếm
            
        Returns:
            Số lượng mục con
        """
        matches = list(self.SUB_ITEM_PATTERN.finditer(text))
        return len(matches)
    
    def _should_split_article(self, clauses: List[Tuple[int, int, str]]) -> bool:
        """
        Quyết định có nên tách điều khoản thành nhiều chunks hay không.
        
        Logic:
        - Nếu chỉ có 1 khoản với danh sách a, b, c... → giữ nguyên (False)
        - Nếu có nhiều khoản rõ rệt → tách (True)
        - Nếu có 2 khoản ngắn → tách để chuẩn hóa (True)
        
        Args:
            clauses: Danh sách các khoản
            
        Returns:
            True nếu nên tách, False nếu giữ nguyên
        """
        if len(clauses) == 0:
            return False
        
        if len(clauses) == 1:
            # Chỉ có 1 khoản, kiểm tra xem có danh sách a, b, c không
            _, _, clause_text = clauses[0]
            sub_items_count = self._count_sub_items(clause_text)
            
            # Nếu có nhiều mục con (a, b, c...), giữ nguyên để tránh mất context
            if sub_items_count >= 3:
                return False
            # Nếu không có hoặc ít mục con, có thể giữ nguyên hoặc tách
            # Nhưng để chuẩn hóa, ta sẽ giữ nguyên nếu chỉ có 1 khoản
            return False
        
        # Có nhiều khoản → nên tách
        return True
    
    def _extract_clause_topic(self, clause_text: str) -> Optional[str]:
        """
        Trích xuất chủ đề/topic của khoản từ nội dung.
        Ví dụ: "Người lao động có các quyền sau đây" → "Quyền của người lao động"
        
        Args:
            clause_text: Nội dung khoản
            
        Returns:
            Topic của khoản hoặc None
        """
        # Lấy 200 ký tự đầu để phân tích
        first_part = clause_text[:200].lower()
        
        # Pattern để tìm topic cụ thể hơn
        topic_patterns = [
            (r'có các quyền', 'Quyền'),
            (r'các quyền', 'Quyền'),
            (r'quyền của', 'Quyền'),
            (r'có các nghĩa vụ', 'Nghĩa vụ'),
            (r'các nghĩa vụ', 'Nghĩa vụ'),
            (r'nghĩa vụ của', 'Nghĩa vụ'),
            (r'có trách nhiệm', 'Trách nhiệm'),
            (r'trách nhiệm của', 'Trách nhiệm'),
            (r'nguyên tắc', 'Nguyên tắc'),
            (r'hình thức', 'Hình thức'),
            (r'thời hạn', 'Thời hạn'),
            (r'điều kiện', 'Điều kiện'),
            (r'nội dung', 'Nội dung'),
            (r'phạm vi', 'Phạm vi'),
        ]
        
        for pattern, topic in topic_patterns:
            if re.search(pattern, first_part):
                # Cố gắng tìm thêm context để làm topic cụ thể hơn
                match = re.search(pattern, first_part)
                if match:
                    # Lấy thêm context xung quanh
                    start = max(0, match.start() - 30)
                    end = min(len(first_part), match.end() + 30)
                    context = clause_text[start:end]
                    
                    # Nếu có "của người lao động" hoặc tương tự, thêm vào topic
                    if 'người lao động' in context.lower():
                        return f"{topic} của người lao động"
                    elif 'người sử dụng lao động' in context.lower():
                        return f"{topic} của người sử dụng lao động"
                    else:
                        return topic
        
        return None
    
    def _determine_content_type(self, clause_text: str) -> str:
        """
        Xác định loại nội dung của khoản.
        
        Args:
            clause_text: Nội dung khoản
            
        Returns:
            Loại nội dung: 'list_requirement', 'definition', 'regulation', etc.
        """
        sub_items_count = self._count_sub_items(clause_text)
        
        if sub_items_count >= 3:
            return 'list_requirement'
        elif 'được hiểu' in clause_text.lower() or 'là' in clause_text.lower()[:50]:
            return 'definition'
        else:
            return 'regulation'
    
    def _create_chunk(
        self,
        article: Dict[str, Any],
        clause_number: Optional[int] = None,
        clause_text: Optional[str] = None,
        is_full_article: bool = False
    ) -> Dict[str, Any]:
        """
        Tạo một chunk từ điều khoản.
        
        Args:
            article: Thông tin điều khoản gốc
            clause_number: Số khoản (None nếu là toàn bộ điều)
            clause_text: Nội dung khoản (None nếu là toàn bộ điều)
            is_full_article: True nếu chunk chứa toàn bộ điều
            
        Returns:
            Dict chứa chunk với format JSON yêu cầu
        """
        metadata = article['metadata']
        original_text = article['text']
        
        # Tạo article_id
        article_number = metadata['article'].replace('Điều ', '')
        article_id = f"Dieu_{article_number}"
        
        # Tạo clause_id
        if clause_number:
            clause_id = f"Khoan_{clause_number}"
        else:
            clause_id = None
        
        # Làm sạch article_title nếu có
        article_title_clean = None
        if metadata.get('article_title'):
            article_title_clean = metadata['article_title']
            # Loại bỏ số khoản ở cuối nếu có
            article_title_clean = re.sub(r'\s+\d+$', '', article_title_clean)
        
        # Tạo text cho chunk
        if is_full_article:
            # Giữ nguyên toàn bộ nội dung
            chunk_text = original_text
        else:
            # Tạo text với format: "Bộ luật Lao động. Điều X. [Tiêu đề]. Khoản Y. [Nội dung]"
            text_parts = []
            
            # Thêm "Bộ luật Lao động" ở đầu
            text_parts.append("Bộ luật Lao động")
            
            # Thêm thông tin chương nếu có
            if metadata.get('chapter'):
                chapter_text = metadata['chapter']
                if metadata.get('chapter_title'):
                    chapter_text += f": {metadata['chapter_title']}"
                text_parts.append(chapter_text)
            
            # Thêm thông tin mục nếu có
            if metadata.get('section'):
                section_text = metadata['section']
                if metadata.get('section_title'):
                    section_text += f": {metadata['section_title']}"
                text_parts.append(section_text)
            
            # Thêm điều khoản
            article_text = metadata['article']
            if metadata.get('article_title'):
                # Làm sạch article_title (có thể chứa số khoản ở cuối)
                article_title = metadata['article_title']
                # Loại bỏ số khoản ở cuối nếu có (ví dụ: "Quyền và nghĩa vụ 1")
                article_title = re.sub(r'\s+\d+$', '', article_title)
                article_text += f". {article_title}"
            text_parts.append(article_text)
            
            # Thêm khoản và nội dung
            if clause_number and clause_text:
                # Loại bỏ số khoản ở đầu clause_text nếu có (để tránh trùng lặp)
                clause_text_clean = re.sub(r'^\d+[\.:]\s+', '', clause_text).strip()
                text_parts.append(f"Khoản {clause_number}.")
                # Thêm toàn bộ nội dung khoản (không thêm dấu chấm thừa)
                if clause_text_clean:
                    text_parts.append(clause_text_clean)
            
            chunk_text = ". ".join(text_parts)
            # Loại bỏ các dấu chấm thừa (ví dụ: "Khoản 1.." -> "Khoản 1.")
            chunk_text = re.sub(r'\.{2,}', '.', chunk_text)
            chunk_text = re.sub(r'\s+\.', '.', chunk_text)  # Loại bỏ khoảng trắng trước dấu chấm
        
        # Tạo metadata cho chunk
        chunk_metadata = {
            "article_id": article_id,
            "article_title": article_title_clean,
            "clause_id": clause_id,
        }
        
        # Thêm topic nếu có khoản
        if clause_text:
            topic = self._extract_clause_topic(clause_text)
            if topic:
                chunk_metadata["topic"] = topic
            
            # Thêm content_type
            content_type = self._determine_content_type(clause_text)
            chunk_metadata["content_type"] = content_type
        
        # Thêm thông tin chương và mục nếu có
        if metadata.get('chapter'):
            chunk_metadata["chapter"] = metadata['chapter']
            chunk_metadata["chapter_title"] = metadata.get('chapter_title')
        
        if metadata.get('section'):
            chunk_metadata["section"] = metadata['section']
            chunk_metadata["section_title"] = metadata.get('section_title')
        
        return {
            "text": chunk_text,
            "metadata": chunk_metadata
        }
    
    def chunk_article(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk một điều khoản thành các chunks nhỏ hơn.
        
        Args:
            article: Thông tin điều khoản
            
        Returns:
            List các chunks
        """
        content = article['text']
        
        # Tìm các khoản trong nội dung
        clauses = self._extract_clauses(content)
        
        # Quyết định có nên tách hay không
        should_split = self._should_split_article(clauses)
        
        chunks = []
        
        if not should_split or len(clauses) == 0:
            # Giữ nguyên toàn bộ điều khoản
            chunk = self._create_chunk(article, is_full_article=True)
            chunks.append(chunk)
        else:
            # Tách thành các chunks theo khoản
            for clause_number, start_pos, clause_text in clauses:
                chunk = self._create_chunk(
                    article,
                    clause_number=clause_number,
                    clause_text=clause_text
                )
                chunks.append(chunk)
        
        return chunks
    
    def process_all(self) -> List[Dict[str, Any]]:
        """
        Xử lý tất cả các điều khoản và tạo chunks.
        
        Returns:
            List tất cả các chunks
        """
        if not self.articles:
            raise ValueError("Chưa load articles. Gọi load_articles() trước.")
        
        all_chunks = []
        
        for i, article in enumerate(self.articles):
            chunks = self.chunk_article(article)
            all_chunks.extend(chunks)
            
            if (i + 1) % 10 == 0:
                print(f"Đã xử lý {i + 1}/{len(self.articles)} điều khoản...")
        
        self.chunks = all_chunks
        print(f"\nĐã tạo {len(all_chunks)} chunks từ {len(self.articles)} điều khoản")
        return all_chunks
    
    def export_to_json(self, output_file: str, indent: int = 2) -> None:
        """
        Export các chunks ra file JSON.
        
        Args:
            output_file: Đường dẫn file JSON để lưu
            indent: Số khoảng trắng để indent JSON (mặc định 2)
        """
        if not self.chunks:
            raise ValueError("Chưa có chunks nào. Gọi process_all() trước.")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=indent)
        
        print(f"Đã export {len(self.chunks)} chunks ra file: {output_path}")


def main():
    """Hàm main để test và chạy thử."""
    # Đường dẫn đến file JSON từ ingest.py
    articles_json = "ai-engine/data/processed/articles.json"
    
    try:
        # Khởi tạo chunker
        chunker = ArticleChunker(articles_json)
        
        # Load articles
        chunker.load_articles()
        
        # Xử lý và tạo chunks
        chunks = chunker.process_all()
        
        # In ra một vài chunks đầu tiên để kiểm tra
        print("\n" + "="*50)
        print("Sample chunks (3 items đầu tiên):")
        print("="*50)
        for i, chunk in enumerate(chunks[:3]):
            print(f"\nChunk {i+1}:")
            print(json.dumps(chunk, ensure_ascii=False, indent=2))
        
        # Export ra file JSON
        output_json = "ai-engine/data/processed/chunks.json"
        chunker.export_to_json(output_json)
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

