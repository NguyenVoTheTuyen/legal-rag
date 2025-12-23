"""
Module để tạo embeddings cho các chunks sử dụng model Vietnamese Bi-Encoder.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import torch


class VietnameseEmbedder:
    """Class để tạo embeddings cho văn bản tiếng Việt."""
    
    def __init__(self, model_name: str = "bkai-foundation-models/vietnamese-bi-encoder"):
        """
        Khởi tạo VietnameseEmbedder.
        
        Args:
            model_name: Tên model từ HuggingFace
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Đang load model {model_name} trên device: {self.device}")
    
    def load_model(self) -> None:
        """Load model từ HuggingFace."""
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            print(f"Đã load model thành công: {self.model_name}")
        except Exception as e:
            raise ValueError(f"Không thể load model: {e}")
    
    def encode(self, texts: List[str], batch_size: int = 32, show_progress_bar: bool = True) -> np.ndarray:
        """
        Encode danh sách văn bản thành vectors.
        
        Args:
            texts: Danh sách các văn bản cần encode
            batch_size: Kích thước batch khi encode
            show_progress_bar: Hiển thị progress bar
            
        Returns:
            Numpy array chứa các vectors (shape: [n_texts, embedding_dim])
        """
        if not self.model:
            raise ValueError("Model chưa được load. Gọi load_model() trước.")
        
        print(f"Đang encode {len(texts)} văn bản...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize để dùng cosine similarity
        )
        
        print(f"Đã encode thành công. Shape: {embeddings.shape}")
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode một văn bản thành vector.
        
        Args:
            text: Văn bản cần encode
            
        Returns:
            Vector embedding (1D numpy array)
        """
        if not self.model:
            raise ValueError("Model chưa được load. Gọi load_model() trước.")
        
        embedding = self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        return embedding[0]


class ChunkEmbedder:
    """Class để embed các chunks từ file JSON."""
    
    def __init__(self, chunks_json_path: str, model_name: str = "bkai-foundation-models/vietnamese-bi-encoder"):
        """
        Khởi tạo ChunkEmbedder.
        
        Args:
            chunks_json_path: Đường dẫn đến file JSON chứa chunks
            model_name: Tên model để embed
        """
        self.chunks_json_path = Path(chunks_json_path)
        if not self.chunks_json_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {chunks_json_path}")
        
        self.embedder = VietnameseEmbedder(model_name)
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
    
    def load_chunks(self) -> None:
        """Đọc các chunks từ file JSON."""
        with open(self.chunks_json_path, 'r', encoding='utf-8') as f:
            self.chunks = json.load(f)
        print(f"Đã load {len(self.chunks)} chunks")
    
    def embed_all(self, batch_size: int = 32) -> np.ndarray:
        """
        Embed tất cả các chunks.
        
        Args:
            batch_size: Kích thước batch khi embed
            
        Returns:
            Numpy array chứa các embeddings
        """
        if not self.chunks:
            raise ValueError("Chưa load chunks. Gọi load_chunks() trước.")
        
        # Load model nếu chưa load
        if not self.embedder.model:
            self.embedder.load_model()
        
        # Lấy danh sách text từ các chunks
        texts = [chunk['text'] for chunk in self.chunks]
        
        # Encode tất cả texts
        self.embeddings = self.embedder.encode(texts, batch_size=batch_size)
        
        return self.embeddings
    
    def save_embeddings(self, output_file: str) -> None:
        """
        Lưu embeddings ra file numpy.
        
        Args:
            output_file: Đường dẫn file để lưu embeddings (.npy)
        """
        if self.embeddings is None:
            raise ValueError("Chưa có embeddings. Gọi embed_all() trước.")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        np.save(output_path, self.embeddings)
        print(f"Đã lưu embeddings ra file: {output_path}")
        print(f"Shape: {self.embeddings.shape}")
    
    def prepare_for_qdrant(self) -> List[Dict[str, Any]]:
        """
        Chuẩn bị dữ liệu để upload lên Qdrant.
        Mỗi point sẽ có: vector, payload (metadata)
        
        Returns:
            List các dict với format Qdrant point
        """
        if self.embeddings is None:
            raise ValueError("Chưa có embeddings. Gọi embed_all() trước.")
        
        points = []
        
        for i, chunk in enumerate(self.chunks):
            point = {
                "id": i,  # Hoặc có thể dùng UUID
                "vector": self.embeddings[i].tolist(),  # Convert numpy array to list
                "payload": {
                    "text": chunk['text'],
                    **chunk['metadata']  # Spread metadata
                }
            }
            points.append(point)
        
        return points
    
    def save_for_qdrant(self, output_file: str) -> None:
        """
        Lưu dữ liệu đã chuẩn bị cho Qdrant ra file JSON.
        
        Args:
            output_file: Đường dẫn file JSON để lưu
        """
        points = self.prepare_for_qdrant()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(points, f, ensure_ascii=False, indent=2)
        
        print(f"Đã lưu {len(points)} points cho Qdrant ra file: {output_path}")


def main():
    """Hàm main để test và chạy thử."""
    # Đường dẫn đến file chunks
    chunks_json = "ai-engine/data/processed/chunks.json"
    
    try:
        # Khởi tạo embedder
        chunk_embedder = ChunkEmbedder(chunks_json)
        
        # Load chunks
        chunk_embedder.load_chunks()
        
        # Embed tất cả chunks
        embeddings = chunk_embedder.embed_all(batch_size=32)
        
        # Lưu embeddings ra file numpy
        embeddings_file = "ai-engine/data/processed/embeddings.npy"
        chunk_embedder.save_embeddings(embeddings_file)
        
        # Chuẩn bị và lưu cho Qdrant
        qdrant_file = "ai-engine/data/processed/qdrant_points.json"
        chunk_embedder.save_for_qdrant(qdrant_file)
        
        print("\n" + "="*50)
        print("Hoàn thành embedding!")
        print(f"- Số lượng chunks: {len(chunk_embedder.chunks)}")
        print(f"- Embedding dimension: {embeddings.shape[1]}")
        print(f"- Embeddings file: {embeddings_file}")
        print(f"- Qdrant points file: {qdrant_file}")
        
    except Exception as e:
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

