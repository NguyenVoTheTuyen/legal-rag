"""
Module để tìm kiếm thông tin pháp lý trên internet sử dụng Tavily AI.
"""

import os
from typing import List, Dict, Any, Optional


class LegalWebSearch:
    """Class để tìm kiếm thông tin pháp lý trên internet."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Khởi tạo LegalWebSearch.
        
        Args:
            api_key: Tavily API key (nếu None sẽ lấy từ env TAVILY_API_KEY)
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY không được thiết lập.\n"
                "Hãy set environment variable: export TAVILY_API_KEY='tvly-xxxxx'\n"
                "Hoặc truyền vào constructor: LegalWebSearch(api_key='tvly-xxxxx')\n"
                "Đăng ký API key miễn phí tại: https://tavily.com"
            )
        
        # Import here to avoid dependency if not using web search
        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "Tavily package chưa được cài đặt.\n"
                "Hãy cài đặt: pip install tavily-python"
            )
    
    def search(
        self,
        query: str,
        max_results: int = 3,
        search_depth: str = "advanced",
        include_domains: Optional[List[str]] = None,
        include_answer: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm thông tin pháp lý trên internet.
        
        Args:
            query: Câu hỏi tìm kiếm
            max_results: Số kết quả tối đa (mặc định: 3)
            search_depth: "basic" hoặc "advanced" (mặc định: advanced)
            include_domains: Danh sách domain ưu tiên (None = dùng mặc định)
            include_answer: Có lấy answer tóm tắt từ Tavily không
            
        Returns:
            List các kết quả tìm kiếm:
            [
                {
                    "type": "answer" | "article",
                    "content": str,
                    "title": str (chỉ với article),
                    "url": str (chỉ với article),
                    "score": float (chỉ với article),
                    "source": str
                }
            ]
        """
        # Domains ưu tiên cho pháp luật Việt Nam
        if include_domains is None:
            include_domains = [
                "thuvienphapluat.vn",
                "luatvietnam.vn",
                "moj.gov.vn",  # Bộ Tư pháp
                "molisa.gov.vn",  # Bộ Lao động - Thương binh và Xã hội
                "chinhphu.vn",  # Cổng thông tin điện tử Chính phủ
            ]
        
        try:
            print(f"\n[Web Search] Đang tìm kiếm trên internet: '{query}'")
            print(f"[Web Search] Ưu tiên domains: {', '.join(include_domains[:3])}...")
            
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_domains=include_domains,
                include_answer=include_answer
            )
            
            results = []
            
            # Add Tavily's generated answer if available
            if include_answer and response.get("answer"):
                results.append({
                    "type": "answer",
                    "content": response["answer"],
                    "source": "Tavily AI Summary"
                })
                print(f"[Web Search] ✓ Có answer tóm tắt từ Tavily")
            
            # Add search results
            for item in response.get("results", []):
                results.append({
                    "type": "article",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0.0),
                    "source": "Web Search"
                })
            
            print(f"[Web Search] ✓ Tìm thấy {len(results)} kết quả từ internet")
            return results
            
        except Exception as e:
            print(f"[Web Search] ✗ Lỗi khi tìm kiếm web: {e}")
            return []
    
    def search_vietnamese_law(
        self,
        query: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm pháp luật Việt Nam với query được tối ưu.
        
        Args:
            query: Câu hỏi tìm kiếm
            max_results: Số kết quả tối đa
            
        Returns:
            List các kết quả tìm kiếm
        """
        # Tối ưu query cho pháp luật Việt Nam
        optimized_query = f"Bộ luật lao động Việt Nam {query}"
        
        return self.search(
            query=optimized_query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True
        )


def main():
    """Test function."""
    import sys
    
    # Check API key
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("✗ TAVILY_API_KEY chưa được thiết lập!")
        print("\nĐể test, hãy:")
        print("1. Đăng ký API key tại: https://tavily.com")
        print("2. Set environment variable:")
        print("   export TAVILY_API_KEY='tvly-xxxxx'")
        print("3. Chạy lại script này")
        sys.exit(1)
    
    try:
        # Initialize
        searcher = LegalWebSearch()
        
        # Test search
        print("=" * 80)
        print("TEST TAVILY WEB SEARCH")
        print("=" * 80)
        
        query = "lương thử việc theo quy định mới nhất"
        print(f"\nQuery: {query}\n")
        
        results = searcher.search_vietnamese_law(query, max_results=3)
        
        # Display results
        print("\n" + "=" * 80)
        print("KẾT QUẢ")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] Type: {result['type']}")
            print(f"Source: {result['source']}")
            
            if result['type'] == 'answer':
                print(f"Content: {result['content']}")
            else:
                print(f"Title: {result.get('title', 'N/A')}")
                print(f"URL: {result.get('url', 'N/A')}")
                print(f"Score: {result.get('score', 0):.4f}")
                content = result.get('content', '')
                if len(content) > 200:
                    print(f"Content: {content[:200]}...")
                else:
                    print(f"Content: {content}")
            
            print("-" * 80)
        
        print(f"\n✓ Test hoàn thành! Tìm thấy {len(results)} kết quả.")
        
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
