"""
Module để upload embeddings lên Qdrant vector database.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models


class QdrantUploader:
    """Class để upload embeddings lên Qdrant."""
    
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "legal_documents",
        vector_size: int = 768  # Dimension của vietnamese-bi-encoder
    ):
        """
        Khởi tạo QdrantUploader.
        
        Args:
            qdrant_url: URL của Qdrant server
            collection_name: Tên collection trong Qdrant
            vector_size: Kích thước vector (dimension)
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.client: Optional[QdrantClient] = None
    
    def connect(self) -> None:
        """Kết nối với Qdrant server."""
        try:
            self.client = QdrantClient(url=self.qdrant_url)
            print(f"Đã kết nối với Qdrant tại: {self.qdrant_url}")
        except Exception as e:
            raise ConnectionError(f"Không thể kết nối với Qdrant: {e}")
    
    def create_collection(self, recreate: bool = False) -> None:
        """
        Tạo collection trong Qdrant.
        
        Args:
            recreate: Nếu True, xóa collection cũ nếu tồn tại và tạo mới
        """
        if not self.client:
            raise ValueError("Chưa kết nối với Qdrant. Gọi connect() trước.")
        
        # Kiểm tra xem collection đã tồn tại chưa
        collections = self.client.get_collections()
        collection_exists = any(
            col.name == self.collection_name 
            for col in collections.collections
        )
        
        if collection_exists:
            if recreate:
                print(f"Đang xóa collection cũ: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            else:
                print(f"Collection {self.collection_name} đã tồn tại. Bỏ qua tạo mới.")
                return
        
        # Tạo collection mới
        print(f"Đang tạo collection: {self.collection_name}")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE  # Dùng cosine similarity
            )
        )
        print(f"Đã tạo collection thành công: {self.collection_name}")
    
    def upload_points(self, points: List[Dict[str, Any]], batch_size: int = 100) -> None:
        """
        Upload các points lên Qdrant.
        
        Args:
            points: List các points với format:
                {
                    "id": int,
                    "vector": List[float],
                    "payload": Dict[str, Any]
                }
            batch_size: Kích thước batch khi upload
        """
        if not self.client:
            raise ValueError("Chưa kết nối với Qdrant. Gọi connect() trước.")
        
        # Convert points sang PointStruct
        qdrant_points = []
        for point in points:
            qdrant_point = PointStruct(
                id=point['id'],
                vector=point['vector'],
                payload=point['payload']
            )
            qdrant_points.append(qdrant_point)
        
        # Upload theo batch
        total = len(qdrant_points)
        print(f"Đang upload {total} points lên Qdrant...")
        
        for i in range(0, total, batch_size):
            batch = qdrant_points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            print(f"Đã upload {min(i + batch_size, total)}/{total} points...")
        
        print(f"Hoàn thành upload {total} points!")
    
    def upload_from_file(self, qdrant_points_file: str) -> None:
        """
        Upload points từ file JSON.
        
        Args:
            qdrant_points_file: Đường dẫn đến file JSON chứa points
        """
        file_path = Path(qdrant_points_file)
        if not file_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {qdrant_points_file}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            points = json.load(f)
        
        self.upload_points(points)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về collection.
        
        Returns:
            Dict chứa thông tin collection
        """
        if not self.client:
            raise ValueError("Chưa kết nối với Qdrant. Gọi connect() trước.")
        
        collection_info = self.client.get_collection(self.collection_name)
        
        # Lấy thông tin từ collection_info
        # CollectionInfo có các thuộc tính: points_count, config, etc.
        try:
            vectors_config = collection_info.config.params.vectors
            vector_size = vectors_config.size if hasattr(vectors_config, 'size') else self.vector_size
            distance = str(vectors_config.distance) if hasattr(vectors_config, 'distance') else "Cosine"
        except Exception:
            # Fallback nếu không lấy được config
            vector_size = self.vector_size
            distance = "Cosine"
        
        return {
            "name": self.collection_name,
            "vectors_count": collection_info.points_count,
            "vectors_config": {
                "size": vector_size,
                "distance": distance
            }
        }


def main():
    """Hàm main để test và upload."""
    # Đường dẫn đến file Qdrant points
    qdrant_points_file = "ai-engine/data/processed/qdrant_points.json"
    
    try:
        # Khởi tạo uploader
        uploader = QdrantUploader(
            qdrant_url="http://localhost:6333",
            collection_name="legal_documents",
            vector_size=768
        )
        
        # Kết nối với Qdrant
        uploader.connect()
        
        # Tạo collection (nếu chưa có)
        uploader.create_collection(recreate=False)
        
        # Upload points từ file
        uploader.upload_from_file(qdrant_points_file)
        
        # Hiển thị thông tin collection
        info = uploader.get_collection_info()
        print("\n" + "="*50)
        print("Thông tin collection:")
        print(f"- Tên: {info['name']}")
        print(f"- Số lượng vectors: {info['vectors_count']}")
        print(f"- Vector size: {info['vectors_config']['size']}")
        print(f"- Distance: {info['vectors_config']['distance']}")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

