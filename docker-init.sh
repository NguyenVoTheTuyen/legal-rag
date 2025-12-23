#!/bin/bash
# Docker initialization script for Legal RAG system

set -e

echo "========================================="
echo "Legal RAG Docker Initialization"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Pull Ollama model
echo -e "${YELLOW}Step 1: Pulling Ollama model (qwen2.5:7b)...${NC}"
docker-compose exec ollama ollama pull qwen2.5:7b
echo -e "${GREEN}✓ Model pulled successfully${NC}"
echo ""

# Step 2: Wait for services to be healthy
echo -e "${YELLOW}Step 2: Waiting for all services to be healthy...${NC}"
sleep 10

# Check Qdrant
echo -n "Checking Qdrant... "
if curl -s -f http://localhost:6333/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Qdrant is not healthy. Please check logs: docker-compose logs qdrant"
    exit 1
fi

# Check Ollama
echo -n "Checking Ollama... "
if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Ollama is not healthy. Please check logs: docker-compose logs ollama"
    exit 1
fi

# Check AI Engine
echo -n "Checking AI Engine... "
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "AI Engine is not healthy. Please check logs: docker-compose logs ai-engine"
    exit 1
fi

# Check Backend API
echo -n "Checking Backend API... "
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Backend API is not healthy. Please check logs: docker-compose logs backend-api"
    exit 1
fi

echo ""
echo -e "${GREEN}All services are healthy!${NC}"
echo ""

# Step 3: Ingest data (if data directory exists and has files)
if [ -d "ai-engine/data/legal_documents" ] && [ "$(ls -A ai-engine/data/legal_documents)" ]; then
    echo -e "${YELLOW}Step 3: Ingesting legal documents into Qdrant...${NC}"
    docker-compose exec ai-engine python run_embedding.py
    echo -e "${GREEN}✓ Data ingested successfully${NC}"
else
    echo -e "${YELLOW}Step 3: Skipping data ingestion (no documents found in ai-engine/data/legal_documents)${NC}"
    echo "To ingest data later, run: docker-compose exec ai-engine python run_embedding.py"
fi

echo ""
echo "========================================="
echo -e "${GREEN}Initialization Complete!${NC}"
echo "========================================="
echo ""
echo "Services are running at:"
echo "  - Backend API:  http://localhost:8080"
echo "  - AI Engine:    http://localhost:8000"
echo "  - Qdrant:       http://localhost:6333"
echo "  - Ollama:       http://localhost:11434"
echo ""
echo "Test the system:"
echo "  curl -X POST http://localhost:8080/api/legal-query \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"question\": \"Thời gian thử việc tối đa bao nhiêu ngày?\"}'"
echo ""
