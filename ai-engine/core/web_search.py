"""
Module để tìm kiếm thông tin pháp lý trên internet sử dụng SearXNG (self-hosted).
"""

import os
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode


class LegalWebSearch:
    """Class để tìm kiếm thông tin pháp lý trên internet sử dụng SearXNG."""
    
    def __init__(self, searxng_url: Optional[str] = None):
        """
        Khởi tạo LegalWebSearch.
        
        Args:
            searxng_url: URL của SearXNG instance (nếu None sẽ lấy từ env SEARXNG_URL)
        """
        self.searxng_url = searxng_url or os.getenv("SEARXNG_URL", "http://localhost:8888")
        
        # Remove trailing slash if present
        self.searxng_url = self.searxng_url.rstrip('/')
        
        # Test connection
        try:
            response = requests.get(f"{self.searxng_url}/healthz", timeout=5)
            if response.status_code != 200:
                print(f"⚠️  Warning: SearXNG health check failed at {self.searxng_url}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Warning: Cannot connect to SearXNG at {self.searxng_url}: {e}")
            print(f"   Make sure SearXNG is running (docker-compose up -d searxng)")
    
    def search(
        self,
        query: str,
        max_results: int = 3,
        language: str = "vi",
        categories: str = "general",
        engines: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm thông tin pháp lý trên internet.
        
        Args:
            query: Câu hỏi tìm kiếm
            max_results: Số kết quả tối đa (mặc định: 3)
            language: Ngôn ngữ tìm kiếm (mặc định: vi - Vietnamese)
            categories: Loại tìm kiếm (mặc định: general)
            engines: Danh sách search engines (None = dùng mặc định)
            
        Returns:
            List các kết quả tìm kiếm:
            [
                {
                    "type": "article",
                    "content": str,
                    "title": str,
                    "url": str,
                    "score": float,
                    "source": str,
                    "engine": str
                }
            ]
        """
        try:
            print(f"\n[Web Search] Đang tìm kiếm trên SearXNG: '{query}'")
            
            # Build search data for POST request
            data = {
                'q': query,
                'format': 'json',
                'language': language,
                'categories': categories,
            }
            
            # Add specific engines if provided
            if engines:
                data['engines'] = ','.join(engines)
            
            # Make POST request to SearXNG (GET requests are often blocked)
            search_url = f"{self.searxng_url}/search"
            response = requests.post(
                search_url,
                data=data,
                timeout=30,
                headers={
                    'User-Agent': 'Legal-RAG-Bot/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            
            if response.status_code != 200:
                print(f"[Web Search] ✗ SearXNG returned status {response.status_code}")
                return []
            
            data = response.json()
            results = []
            
            # Process search results
            for item in data.get('results', [])[:max_results]:
                # Calculate a simple relevance score (SearXNG doesn't provide scores)
                # We'll use position as inverse score (first result = highest score)
                position = len(results) + 1
                score = 1.0 - (position * 0.1)  # 1.0, 0.9, 0.8, etc.
                
                results.append({
                    "type": "article",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": max(0.1, score),  # Minimum score of 0.1
                    "source": "Web Search",
                    "engine": item.get("engine", "unknown")
                })
            
            print(f"[Web Search] ✓ Tìm thấy {len(results)} kết quả từ SearXNG")
            
            # Print engines used
            engines_used = set(r.get("engine", "unknown") for r in results)
            if engines_used:
                print(f"[Web Search] Engines: {', '.join(engines_used)}")
            
            return results
            
        except requests.exceptions.Timeout:
            print(f"[Web Search] ✗ Timeout khi tìm kiếm (>30s)")
            return []
        except requests.exceptions.RequestException as e:
            print(f"[Web Search] ✗ Lỗi kết nối đến SearXNG: {e}")
            return []
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
            language="vi",
            categories="general"
        )
    
    def search_specific_domains(
        self,
        query: str,
        domains: List[str],
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm trên các domain cụ thể.
        
        Args:
            query: Câu hỏi tìm kiếm
            domains: Danh sách domain (vd: ["thuvienphapluat.vn", "luatvietnam.vn"])
            max_results: Số kết quả tối đa
            
        Returns:
            List các kết quả tìm kiếm
        """
        # Add site: operator for each domain
        domain_query = " OR ".join([f"site:{domain}" for domain in domains])
        full_query = f"{query} ({domain_query})"
        
        return self.search(
            query=full_query,
            max_results=max_results,
            language="vi"
        )


def main():
    """Test function."""
    import sys
    
    # Check SearXNG URL
    searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8888")
    print(f"SearXNG URL: {searxng_url}")
    
    try:
        # Initialize
        searcher = LegalWebSearch()
        
        # Test search
        print("=" * 80)
        print("TEST SEARXNG WEB SEARCH")
        print("=" * 80)
        
        query = "lương thử việc theo quy định mới nhất"
        print(f"\nQuery: {query}\n")
        
        results = searcher.search_vietnamese_law(query, max_results=3)
        
        # Display results
        print("\n" + "=" * 80)
        print("KẾT QUẢ")
        print("=" * 80)
        
        if not results:
            print("\n✗ Không tìm thấy kết quả nào!")
            print("\nKiểm tra:")
            print("1. SearXNG có đang chạy không? (docker-compose up -d searxng)")
            print("2. Truy cập http://localhost:8888 để test")
            print(f"3. SEARXNG_URL={searxng_url} có đúng không?")
            sys.exit(1)
        
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] Type: {result['type']}")
            print(f"Source: {result['source']}")
            print(f"Engine: {result.get('engine', 'N/A')}")
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
