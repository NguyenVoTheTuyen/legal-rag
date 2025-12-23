#!/usr/bin/env python3
"""
Script để chạy pipeline embedding và upload Qdrant.
Có thể chạy trực tiếp: python run_embedding.py
"""

import sys
from pathlib import Path

# Thêm thư mục embedding vào path
sys.path.insert(0, str(Path(__file__).parent / "embedding"))

from embedding.embedder import ChunkEmbedder
from embedding.qdrant_uploader import QdrantUploader


def run_pipeline(
    chunks_json: str = "ai-engine/data/processed/chunks.json",
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "legal_documents",
    batch_size: int = 32,
    recreate_collection: bool = False
):
    """
    Chạy toàn bộ pipeline: Embed chunks và upload lên Qdrant.
    
    Args:
        chunks_json: Đường dẫn đến file chunks.json
        qdrant_url: URL của Qdrant server
        collection_name: Tên collection trong Qdrant
        batch_size: Kích thước batch khi embed
        recreate_collection: Nếu True, xóa collection cũ và tạo mới
    """
    print("="*50)
    print("Bắt đầu pipeline embedding và upload Qdrant")
    print("="*50)
    
    # Bước 1: Embed chunks
    print("\n[1/2] Đang embed chunks...")
    chunk_embedder = ChunkEmbedder(chunks_json)
    chunk_embedder.load_chunks()
    chunk_embedder.embed_all(batch_size=batch_size)
    
    # Lưu embeddings và Qdrant points
    embeddings_file = "ai-engine/data/processed/embeddings.npy"
    qdrant_points_file = "ai-engine/data/processed/qdrant_points.json"
    
    chunk_embedder.save_embeddings(embeddings_file)
    chunk_embedder.save_for_qdrant(qdrant_points_file)
    
    print(f"✓ Đã embed {len(chunk_embedder.chunks)} chunks")
    print(f"✓ Embedding dimension: {chunk_embedder.embeddings.shape[1]}")
    
    # Bước 2: Upload lên Qdrant
    print("\n[2/2] Đang upload lên Qdrant...")
    uploader = QdrantUploader(
        qdrant_url=qdrant_url,
        collection_name=collection_name,
        vector_size=chunk_embedder.embeddings.shape[1]
    )
    
    uploader.connect()
    uploader.create_collection(recreate=recreate_collection)
    uploader.upload_from_file(qdrant_points_file)
    
    # Hiển thị thông tin collection
    info = uploader.get_collection_info()
    print(f"✓ Đã upload {info['vectors_count']} vectors lên Qdrant")
    
    print("\n" + "="*50)
    print("Hoàn thành pipeline!")
    print("="*50)
    print(f"- Collection: {collection_name}")
    print(f"- Vectors: {info['vectors_count']}")
    print(f"- Vector size: {info['vectors_config']['size']}")
    print(f"- Distance: {info['vectors_config']['distance']}")


def main():
    """Hàm main."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline embedding và upload Qdrant")
    parser.add_argument(
        "--chunks",
        type=str,
        default="ai-engine/data/processed/chunks.json",
        help="Đường dẫn đến file chunks.json"
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
        "--batch-size",
        type=int,
        default=32,
        help="Kích thước batch khi embed"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Xóa collection cũ và tạo mới"
    )
    
    args = parser.parse_args()
    
    run_pipeline(
        chunks_json=args.chunks,
        qdrant_url=args.qdrant_url,
        collection_name=args.collection,
        batch_size=args.batch_size,
        recreate_collection=args.recreate
    )


if __name__ == "__main__":
    main()

