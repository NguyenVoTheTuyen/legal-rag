#!/usr/bin/env python3
"""
FastAPI HTTP Server cho Legal RAG AI Engine.
Expose Agentic RAG qua HTTP REST API.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from dotenv import load_dotenv
load_dotenv()

# Thêm thư mục hiện tại vào path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from contextlib import asynccontextmanager
import uvicorn

from core.agentic_rag import LegalRAGAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic Models
class QueryRequest(BaseModel):
    """Request model cho query endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Thời gian thử việc tối đa bao nhiêu ngày?",
                "max_iterations": 3,
                "top_k": 3,
                "enable_web_search": True
            }
        }
    )
    
    question: str = Field(..., description="Câu hỏi cần tìm kiếm", min_length=1)
    max_iterations: Optional[int] = Field(3, description="Số lần tìm kiếm tối đa", ge=1, le=10)
    top_k: Optional[int] = Field(3, description="Số lượng kết quả mỗi lần tìm kiếm", ge=1, le=20)
    enable_web_search: Optional[bool] = Field(True, description="Bật tìm kiếm web")


class SearchResult(BaseModel):
    """Model cho một kết quả tìm kiếm."""
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None
    source_type: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model cho query endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "answer": "Theo Điều 24 Bộ luật Lao động 2019...",
                "search_results": [],
                "web_results": [],
                "iterations": 2,
                "query_used": "thời gian thử việc tối đa"
            }
        }
    )
    
    answer: str = Field(..., description="Câu trả lời được tạo")
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="Kết quả tìm kiếm nội bộ")
    web_results: List[Dict[str, Any]] = Field(default_factory=list, description="Kết quả tìm kiếm web")
    iterations: int = Field(..., description="Số lần tìm kiếm đã thực hiện")
    query_used: str = Field(..., description="Query cuối cùng được sử dụng")


class HealthResponse(BaseModel):
    """Response model cho health check."""
    status: str
    service: str
    version: str


# Global agent instance
agent: Optional[LegalRAGAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler cho startup và shutdown."""
    global agent
    
    # Startup
    logger.info("Starting Legal RAG AI Engine...")
    
    # Load configuration from environment or use defaults
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection_name = os.getenv("COLLECTION_NAME", "legal_documents")
    ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    tavily_api_key = os.getenv("TAVILY_API_KEY", "")
    
    try:
        agent = LegalRAGAgent(
            qdrant_url=qdrant_url,
            collection_name=collection_name,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            tavily_api_key=tavily_api_key,
            enable_web_search=True
        )
        agent.initialize()
        logger.info("✓ Legal RAG Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal RAG AI Engine...")


# FastAPI App
app = FastAPI(
    title="Legal RAG AI Engine API",
    description="HTTP REST API cho hệ thống Agentic RAG pháp lý",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên giới hạn origins cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": "Legal RAG AI Engine",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if agent is not None else "unhealthy",
        service="Legal RAG AI Engine",
        version="1.0.0"
    )


@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def query_legal_rag(request: QueryRequest):
    """
    Main endpoint để query Legal RAG system.
    
    Args:
        request: QueryRequest với question và các tham số tùy chọn
        
    Returns:
        QueryResponse với answer và search results
        
    Raises:
        HTTPException: Nếu có lỗi trong quá trình xử lý
    """
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent chưa được khởi tạo"
        )
    
    try:
        logger.info(f"Received query: {request.question}")
        
        # Update agent configuration if needed
        if request.max_iterations:
            agent.max_iterations = request.max_iterations
        if request.top_k:
            agent.top_k = request.top_k
        if request.enable_web_search is not None:
            agent.enable_web_search = request.enable_web_search
        
        # Execute query
        result = agent.query(request.question)
        
        logger.info(f"Query completed: {result['iterations']} iterations, "
                   f"{len(result['search_results'])} internal results, "
                   f"{len(result.get('web_results', []))} web results")
        
        return QueryResponse(
            answer=result["answer"],
            search_results=result.get("search_results", []),
            web_results=result.get("web_results", []),
            iterations=result["iterations"],
            query_used=result["query_used"]
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý câu hỏi: {str(e)}"
        )


def main():
    """Main function để chạy server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Legal RAG AI Engine HTTP Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
