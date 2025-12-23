# Agentic RAG với LangGraph

Hệ thống RAG đã được nâng cấp từ RAG đơn giản sang **Agentic RAG** sử dụng LangGraph, cho phép agent tự động quyết định và thực hiện các bước tìm kiếm thông minh.

## Tính năng mới

### So với RAG truyền thống:
- ✅ **Tự động quyết định**: Agent tự quyết định khi nào cần tìm kiếm, khi nào cần tinh chỉnh query
- ✅ **Tìm kiếm nhiều bước**: Có thể thực hiện nhiều lần tìm kiếm với các query khác nhau
- ✅ **Tinh chỉnh query thông minh**: Tự động cải thiện query để tìm kết quả tốt hơn
- ✅ **Workflow linh hoạt**: Sử dụng LangGraph để quản lý workflow phức tạp

## Cài đặt

```bash
# Cài đặt dependencies
pip install -r requirements.txt
```

## Sử dụng

### 1. Chạy trực tiếp với script

```bash
python run_agentic_rag.py "Thời gian thử việc tối đa bao nhiêu ngày?"
```

### 2. Với các tùy chọn

```bash
python run_agentic_rag.py "Quy định về nghỉ phép năm" \
  --max-iterations 5 \
  --top-k 5 \
  --show-results
```

### 3. Sử dụng trong code Python

```python
from core.agentic_rag import LegalRAGAgent

# Khởi tạo agent
agent = LegalRAGAgent(
    qdrant_url="http://localhost:6333",
    collection_name="legal_documents",
    ollama_url="http://127.0.0.1:11434",
    ollama_model="llama3.2",
    max_iterations=3,
    top_k=3
)

# Khởi tạo
agent.initialize()

# Thực hiện query
result = agent.query("Câu hỏi của bạn")

# Kết quả
print(result["answer"])
print(result["search_results"])
print(result["iterations"])
```

## Workflow của Agentic RAG

```
1. Decide Action
   ├─> Chưa có kết quả → Search
   ├─> Cần refine query → Refine Query → Search
   └─> Đã đủ thông tin → Generate Answer

2. Search
   ├─> Cần tìm thêm → Continue (quay lại Decide)
   └─> Đã đủ → Generate Answer

3. Generate Answer → End
```

## Tham số

- `max_iterations`: Số lần tìm kiếm tối đa (mặc định: 3)
- `top_k`: Số lượng kết quả mỗi lần tìm kiếm (mặc định: 3)
- `ollama_model`: Model Ollama để sử dụng (mặc định: llama3.2)
- `qdrant_url`: URL của Qdrant server
- `collection_name`: Tên collection trong Qdrant

## So sánh với RAG cũ

### RAG truyền thống (`search.py`):
- Tìm kiếm 1 lần với query gốc
- Trả về kết quả và generate answer

### Agentic RAG (`agentic_rag.py`):
- Tự động quyết định số lần tìm kiếm
- Tinh chỉnh query nếu cần
- Tích lũy kết quả từ nhiều lần tìm kiếm
- Tạo câu trả lời dựa trên tất cả kết quả

## Lưu ý

1. Đảm bảo Ollama đang chạy trước khi sử dụng
2. Đảm bảo Qdrant đang chạy và đã có collection `legal_documents`
3. Model embedding mặc định: `bkai-foundation-models/vietnamese-bi-encoder`

