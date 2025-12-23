# Legal RAG Backend API

Go HTTP server that acts as a gateway between clients and the Python AI Engine for the Legal RAG system.

## Architecture

```
Client → Go Backend (port 8080) → Python AI Engine (port 8000)
```

## Features

- **HTTP REST API** for client requests
- **HTTP Client** to communicate with Python AI Engine
- **Request validation** and error handling
- **CORS support** for cross-origin requests
- **Health check** endpoints
- **Logging** middleware

## Prerequisites

- Go 1.21 or higher
- Python AI Engine running on port 8000

## Installation

1. Install dependencies:
```bash
go mod download
```

2. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GO_SERVER_PORT` | Port for Go server | `8080` |
| `PYTHON_AI_ENGINE_URL` | URL of Python AI Engine | `http://localhost:8000` |
| `REQUEST_TIMEOUT` | Timeout for requests to Python service | `60s` |

## Running the Server

### Development Mode

```bash
go run main.go
```

### Production Build

```bash
# Build binary
go build -o legal-rag-backend main.go

# Run binary
./legal-rag-backend
```

## API Endpoints

### Root
- **GET** `/`
- Returns service information

### Health Check
- **GET** `/health`
- Returns health status of the Go backend

**Response:**
```json
{
  "status": "healthy",
  "service": "Legal RAG Backend API",
  "version": "1.0.0"
}
```

### Legal Query
- **POST** `/api/legal-query`
- Main endpoint to query the Legal RAG system

**Request Body:**
```json
{
  "question": "Thời gian thử việc tối đa bao nhiêu ngày?",
  "max_iterations": 3,
  "top_k": 3,
  "enable_web_search": true
}
```

**Response:**
```json
{
  "answer": "Theo Điều 24 Bộ luật Lao động 2019...",
  "search_results": [...],
  "web_results": [...],
  "iterations": 2,
  "query_used": "thời gian thử việc tối đa"
}
```

## Example Usage

### Using curl

```bash
# Health check
curl http://localhost:8080/health

# Query
curl -X POST http://localhost:8080/api/legal-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quy định về nghỉ phép năm"
  }'
```

### Using httpie

```bash
# Health check
http GET http://localhost:8080/health

# Query
http POST http://localhost:8080/api/legal-query \
  question="Quy định về nghỉ phép năm"
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request format
- `500 Internal Server Error` - Error processing request or communicating with Python service
- `503 Service Unavailable` - Python AI Engine is not available

Error response format:
```json
{
  "error": "error_code",
  "message": "Detailed error message"
}
```

## Development

### Project Structure

```
backend-api/
├── main.go           # Main application file
├── go.mod            # Go module definition
├── go.sum            # Go dependencies checksums
├── .env.example      # Environment variables example
└── README.md         # This file
```

### Adding New Endpoints

1. Define handler function in `main.go`
2. Register route in the `main()` function
3. Update this README with endpoint documentation

## Troubleshooting

### Python AI Engine Connection Failed

If you see errors like "health check failed", ensure:
1. Python AI Engine is running on the configured port (default: 8000)
2. The `PYTHON_AI_ENGINE_URL` is correct
3. No firewall blocking the connection

### Port Already in Use

If port 8080 is already in use:
1. Change `GO_SERVER_PORT` in `.env`
2. Or set environment variable: `GO_SERVER_PORT=8081 go run main.go`

## License

MIT
