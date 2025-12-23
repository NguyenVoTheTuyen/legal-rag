"""
Module để ingest và xử lý văn bản pháp luật từ file Word.
Tách văn bản theo cấu trúc phân cấp: Chương → Mục → Điều và làm sạch dữ liệu.

Cấu trúc phân cấp:
- Chương (Chapter): Chương I, Chương II, ...
- Mục (Section): Mục 1, Mục 2, ... (có thể có hoặc không)
- Điều (Article): Điều 1, Điều 2, ...
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from docx import Document


class DocumentIngester:
    """Class để ingest và xử lý tài liệu Word."""
    
    # Pattern để tìm các chương: "Chương" + số La Mã hoặc số thường
    CHAPTER_PATTERN = re.compile(
        r'^Chương\s+([IVX]+|\d+)[\.:]?\s*(.+?)$', 
        re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern để tìm các mục: "Mục" + số
    SECTION_PATTERN = re.compile(
        r'^Mục\s+(\d+)[\.:]?\s*(.+?)$', 
        re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern để tìm các điều khoản: "Điều" + số + dấu chấm/dấu hai chấm
    ARTICLE_PATTERN = re.compile(r'^Điều\s+(\d+)[\.:]', re.IGNORECASE | re.MULTILINE)
    
    # Pattern để loại bỏ header/footer và số trang
    HEADER_FOOTER_PATTERN = re.compile(
        r'(Trang\s*\d+|Page\s*\d+|^\d+$|^-\s*\d+\s*-$)', 
        re.IGNORECASE | re.MULTILINE
    )
    
    def __init__(self, file_path: str):
        """
        Khởi tạo DocumentIngester.
        
        Args:
            file_path: Đường dẫn đến file Word cần xử lý
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {file_path}")
        
        self.document: Optional[Document] = None
        self.raw_text: str = ""
        self.articles: List[Dict[str, str]] = []
        self.current_chapter: Optional[Dict[str, str]] = None
    
    def load_document(self) -> None:
        """Đọc file Word và lưu vào document."""
        try:
            self.document = Document(self.file_path)
        except Exception as e:
            raise ValueError(f"Không thể đọc file Word: {e}")
    
    def extract_text(self) -> str:
        """
        Trích xuất toàn bộ văn bản từ document.
        
        Returns:
            Chuỗi văn bản đã được làm sạch
        """
        if not self.document:
            raise ValueError("Document chưa được load. Gọi load_document() trước.")
        
        paragraphs = []
        for paragraph in self.document.paragraphs:
            text = paragraph.text.strip()
            if text:
                paragraphs.append(text)
        
        # Nối các đoạn văn bằng newline
        full_text = '\n'.join(paragraphs)
        
        # Làm sạch: xóa header, footer, số trang
        cleaned_text = self._clean_text(full_text)
        
        self.raw_text = cleaned_text
        return cleaned_text
    
    def _clean_text(self, text: str) -> str:
        """
        Làm sạch văn bản: xóa header, footer, số trang.
        
        Args:
            text: Văn bản gốc
            
        Returns:
            Văn bản đã được làm sạch
        """
        # Xóa các dòng chỉ chứa số (số trang)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Bỏ qua dòng rỗng
            if not line:
                continue
            
            # Bỏ qua dòng chỉ chứa số (số trang)
            if re.match(r'^\d+$', line):
                continue
            
            # Bỏ qua pattern header/footer
            if self.HEADER_FOOTER_PATTERN.match(line):
                continue
            
            # Bỏ qua các dòng quá ngắn có thể là header/footer
            if len(line) < 3 and line.isdigit():
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _find_current_chapter(self, text: str, position: int) -> Optional[Dict[str, str]]:
        """
        Tìm chương hiện tại dựa trên vị trí trong văn bản.
        
        Args:
            text: Toàn bộ văn bản
            position: Vị trí hiện tại trong văn bản
            
        Returns:
            Dict chứa thông tin chương: 'chapter_number', 'chapter_title'
        """
        # Tìm tất cả các chương
        chapter_matches = list(self.CHAPTER_PATTERN.finditer(text))
        
        if not chapter_matches:
            return None
        
        # Tìm chương gần nhất trước vị trí hiện tại
        current_chapter = None
        for match in chapter_matches:
            if match.start() <= position:
                chapter_number = match.group(1)
                chapter_title = match.group(2).strip() if match.group(2) else ""
                current_chapter = {
                    'chapter_number': chapter_number,
                    'chapter_title': chapter_title
                }
            else:
                break
        
        return current_chapter
    
    def _find_current_section(self, text: str, position: int) -> Optional[Dict[str, str]]:
        """
        Tìm mục hiện tại dựa trên vị trí trong văn bản.
        
        Args:
            text: Toàn bộ văn bản
            position: Vị trí hiện tại trong văn bản
            
        Returns:
            Dict chứa thông tin mục: 'section_number', 'section_title'
        """
        # Tìm tất cả các mục
        section_matches = list(self.SECTION_PATTERN.finditer(text))
        
        if not section_matches:
            return None
        
        # Tìm mục gần nhất trước vị trí hiện tại
        current_section = None
        for match in section_matches:
            if match.start() <= position:
                section_number = match.group(1)
                section_title = match.group(2).strip() if match.group(2) else ""
                current_section = {
                    'section_number': section_number,
                    'section_title': section_title
                }
            else:
                break
        
        return current_section
    
    def split_by_articles(self, text: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Tách văn bản thành các điều khoản dựa trên pattern "Điều X.".
        Mỗi điều khoản sẽ được gắn với thông tin chương và mục tương ứng.
        
        Args:
            text: Văn bản cần tách. Nếu None, dùng self.raw_text
            
        Returns:
            Danh sách các điều khoản, mỗi điều là dict với keys: 
            'article_number', 'content', 'chapter_number', 'chapter_title',
            'section_number', 'section_title'
        """
        if text is None:
            text = self.raw_text
        
        if not text:
            raise ValueError("Không có văn bản để xử lý. Gọi extract_text() trước.")
        
        # Tìm tất cả các vị trí bắt đầu của các điều khoản
        article_matches = list(self.ARTICLE_PATTERN.finditer(text))
        
        if not article_matches:
            # Nếu không tìm thấy điều khoản, trả về toàn bộ văn bản
            chapter_info = self._find_current_chapter(text, 0)
            section_info = self._find_current_section(text, 0)
            return [{
                'article_number': '0',
                'content': text,
                'chapter_number': chapter_info['chapter_number'] if chapter_info else None,
                'chapter_title': chapter_info['chapter_title'] if chapter_info else None,
                'section_number': section_info['section_number'] if section_info else None,
                'section_title': section_info['section_title'] if section_info else None
            }]
        
        articles = []
        
        # Xử lý từng điều khoản
        for i, match in enumerate(article_matches):
            article_number = match.group(1)
            start_pos = match.start()
            
            # Tìm chương và mục hiện tại cho điều khoản này
            chapter_info = self._find_current_chapter(text, start_pos)
            section_info = self._find_current_section(text, start_pos)
            
            # Vị trí kết thúc là vị trí bắt đầu của điều tiếp theo, hoặc cuối văn bản
            if i + 1 < len(article_matches):
                end_pos = article_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            # Trích xuất nội dung điều khoản
            content = text[start_pos:end_pos].strip()
            
            # Làm sạch thêm nội dung
            content = self._clean_article_content(content)
            
            # Trích xuất tiêu đề điều khoản
            article_title = self._extract_article_title(content)
            
            if content:  # Chỉ thêm nếu có nội dung
                article_data = {
                    'article_number': article_number,
                    'content': content,
                    'article_title': article_title
                }
                
                # Thêm thông tin chương nếu có
                if chapter_info:
                    article_data['chapter_number'] = chapter_info['chapter_number']
                    article_data['chapter_title'] = chapter_info['chapter_title']
                else:
                    article_data['chapter_number'] = None
                    article_data['chapter_title'] = None
                
                # Thêm thông tin mục nếu có
                if section_info:
                    article_data['section_number'] = section_info['section_number']
                    article_data['section_title'] = section_info['section_title']
                else:
                    article_data['section_number'] = None
                    article_data['section_title'] = None
                
                articles.append(article_data)
        
        self.articles = articles
        return articles
    
    def _extract_article_title(self, content: str) -> Optional[str]:
        """
        Trích xuất tiêu đề điều khoản từ nội dung.
        Tiêu đề thường là dòng đầu tiên sau "Điều X." hoặc "Điều X:"
        
        Args:
            content: Nội dung điều khoản
            
        Returns:
            Tiêu đề điều khoản hoặc None nếu không tìm thấy
        """
        # Tìm pattern "Điều X. Tiêu đề" hoặc "Điều X: Tiêu đề"
        # Tiêu đề thường kết thúc ở dấu chấm, dấu hai chấm, hoặc xuống dòng
        pattern = r'^Điều\s+\d+[\.:]\s*([^\.\n]+?)(?:\.|$|\n)'
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        
        if match:
            title = match.group(1).strip()
            # Loại bỏ các ký tự thừa
            title = re.sub(r'\s+', ' ', title)
            return title if title else None
        
        return None
    
    def _clean_article_content(self, content: str) -> str:
        """
        Làm sạch nội dung của một điều khoản.
        
        Args:
            content: Nội dung điều khoản
            
        Returns:
            Nội dung đã được làm sạch
        """
        # Xóa các khoảng trắng thừa
        content = re.sub(r'\s+', ' ', content)
        
        # Xóa các dòng trống liên tiếp
        content = re.sub(r'\n\s*\n+', '\n', content)
        
        # Xóa các ký tự đặc biệt không cần thiết ở đầu/cuối
        content = content.strip()
        
        return content
    
    def process(self) -> List[Dict[str, str]]:
        """
        Xử lý toàn bộ pipeline: load document, extract text, split by articles.
        
        Returns:
            Danh sách các điều khoản đã được xử lý
        """
        self.load_document()
        self.extract_text()
        articles = self.split_by_articles()
        return articles
    
    def format_to_json(self) -> List[Dict[str, Any]]:
        """
        Format các điều khoản thành JSON structure theo yêu cầu.
        
        Returns:
            List các dict với format:
            {
                "text": "...",
                "metadata": {
                    "chapter": "Chương I",
                    "chapter_title": "...",
                    "section": "Mục 1" hoặc null,
                    "article": "Điều 2",
                    "article_title": "..."
                }
            }
        """
        if not self.articles:
            raise ValueError("Chưa có điều khoản nào. Gọi process() trước.")
        
        json_data = []
        
        for article in self.articles:
            # Tạo text với format: "Chương X: ... Điều Y. ... (nội dung)"
            text_parts = []
            
            # Thêm thông tin chương
            if article.get('chapter_number'):
                chapter_text = f"Chương {article['chapter_number']}"
                if article.get('chapter_title'):
                    chapter_text += f": {article['chapter_title']}"
                text_parts.append(chapter_text)
            
            # Thêm thông tin mục nếu có
            if article.get('section_number'):
                section_text = f"Mục {article['section_number']}"
                if article.get('section_title'):
                    section_text += f": {article['section_title']}"
                text_parts.append(section_text)
            
            # Thêm điều khoản
            article_text = f"Điều {article['article_number']}"
            if article.get('article_title'):
                article_text += f". {article['article_title']}"
            text_parts.append(article_text)
            
            # Nối các phần với dấu chấm và thêm nội dung
            # Format: "Chương X: ... Điều Y. ... (nội dung điều)"
            text = ". ".join(text_parts) + ". " + article['content']
            
            # Tạo metadata
            metadata = {
                "chapter": f"Chương {article['chapter_number']}" if article.get('chapter_number') else None,
                "chapter_title": article.get('chapter_title'),
                "section": f"Mục {article['section_number']}" if article.get('section_number') else None,
                "article": f"Điều {article['article_number']}",
                "article_title": article.get('article_title')
            }
            
            json_data.append({
                "text": text,
                "metadata": metadata
            })
        
        return json_data
    
    def export_to_json(self, output_file: str, indent: int = 2) -> None:
        """
        Export các điều khoản ra file JSON.
        
        Args:
            output_file: Đường dẫn file JSON để lưu
            indent: Số khoảng trắng để indent JSON (mặc định 2)
        """
        json_data = self.format_to_json()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=indent)
        
        print(f"Đã export {len(json_data)} điều khoản ra file: {output_path}")
    
    def save_articles(self, output_dir: str) -> None:
        """
        Lưu các điều khoản ra file riêng biệt với cấu trúc phân cấp.
        
        Args:
            output_dir: Thư mục để lưu các file
        """
        if not self.articles:
            raise ValueError("Chưa có điều khoản nào. Gọi process() trước.")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for article in self.articles:
            # Tạo tên file với cấu trúc: Chuong_X_Muc_Y_Dieu_Z.txt
            parts = []
            if article.get('chapter_number'):
                parts.append(f"Chuong_{article['chapter_number']}")
            if article.get('section_number'):
                parts.append(f"Muc_{article['section_number']}")
            parts.append(f"Dieu_{article['article_number']}")
            
            filename = "_".join(parts) + ".txt"
            file_path = output_path / filename
            
            # Lưu nội dung với metadata
            content_lines = []
            if article.get('chapter_number'):
                content_lines.append(f"Chương {article['chapter_number']}: {article.get('chapter_title', '')}")
            if article.get('section_number'):
                content_lines.append(f"Mục {article['section_number']}: {article.get('section_title', '')}")
            content_lines.append(f"Điều {article['article_number']}")
            content_lines.append("=" * 50)
            content_lines.append(article['content'])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_lines))
            
            print(f"Đã lưu: {file_path}")


def main():
    """Hàm main để test và chạy thử."""
    # Đường dẫn đến file Word
    file_path = "ai-engine/data/raw/BoLuatLaoDong2019.docx"
    
    try:
        # Khởi tạo ingester
        ingester = DocumentIngester(file_path)
        
        # Xử lý document
        articles = ingester.process()
        
        print(f"Đã tách được {len(articles)} điều khoản")
        print("\n" + "="*50)
        
        # Format và export ra JSON
        json_data = ingester.format_to_json()
        
        # In ra một vài item đầu tiên để kiểm tra
        print("\n" + "="*50)
        print("Sample JSON output (3 items đầu tiên):")
        print("="*50)
        for i, item in enumerate(json_data[:3]):
            print(f"\nItem {i+1}:")
            print(json.dumps(item, ensure_ascii=False, indent=2))
        
        # Export ra file JSON
        output_json = "ai-engine/data/processed/articles.json"
        ingester.export_to_json(output_json)
        
        # Lưu các điều khoản ra file text (tùy chọn)
        # ingester.save_articles("ai-engine/data/processed/articles")
        
    except Exception as e:
        print(f"Lỗi: {e}")


if __name__ == "__main__":
    main()

