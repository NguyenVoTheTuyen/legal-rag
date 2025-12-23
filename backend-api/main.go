package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
)

// Request/Response Models

// LegalQueryRequest represents the request from client
type LegalQueryRequest struct {
	Question         string `json:"question" binding:"required"`
	MaxIterations    *int   `json:"max_iterations,omitempty"`
	TopK             *int   `json:"top_k,omitempty"`
	EnableWebSearch  *bool  `json:"enable_web_search,omitempty"`
}

// PythonQueryRequest represents the request to Python AI engine
type PythonQueryRequest struct {
	Question         string `json:"question"`
	MaxIterations    int    `json:"max_iterations"`
	TopK             int    `json:"top_k"`
	EnableWebSearch  bool   `json:"enable_web_search"`
}

// LegalQueryResponse represents the response to client
type LegalQueryResponse struct {
	Answer        string                   `json:"answer"`
	SearchResults []map[string]interface{} `json:"search_results"`
	WebResults    []map[string]interface{} `json:"web_results"`
	Iterations    int                      `json:"iterations"`
	QueryUsed     string                   `json:"query_used"`
}

// HealthResponse represents health check response
type HealthResponse struct {
	Status  string `json:"status"`
	Service string `json:"service"`
	Version string `json:"version"`
}

// ErrorResponse represents error response
type ErrorResponse struct {
	Error   string `json:"error"`
	Message string `json:"message"`
}

// Configuration
type Config struct {
	ServerPort       string
	PythonEngineURL  string
	RequestTimeout   time.Duration
}

func loadConfig() *Config {
	port := os.Getenv("GO_SERVER_PORT")
	if port == "" {
		port = "8080"
	}

	pythonURL := os.Getenv("PYTHON_AI_ENGINE_URL")
	if pythonURL == "" {
		pythonURL = "http://localhost:8000"
	}

	timeout := 60 * time.Second
	if timeoutStr := os.Getenv("REQUEST_TIMEOUT"); timeoutStr != "" {
		if parsedTimeout, err := time.ParseDuration(timeoutStr); err == nil {
			timeout = parsedTimeout
		}
	}

	return &Config{
		ServerPort:      port,
		PythonEngineURL: pythonURL,
		RequestTimeout:  timeout,
	}
}

// HTTP Client for Python AI Engine
type PythonClient struct {
	baseURL    string
	httpClient *http.Client
}

func NewPythonClient(baseURL string, timeout time.Duration) *PythonClient {
	return &PythonClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: timeout,
		},
	}
}

func (c *PythonClient) Query(req *PythonQueryRequest) (*LegalQueryResponse, error) {
	// Marshal request
	jsonData, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create HTTP request
	url := fmt.Sprintf("%s/api/query", c.baseURL)
	httpReq, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")

	// Send request
	log.Printf("Sending request to Python AI Engine: %s", url)
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	// Check status code
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("python service returned status %d: %s", resp.StatusCode, string(body))
	}

	// Unmarshal response
	var queryResp LegalQueryResponse
	if err := json.Unmarshal(body, &queryResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &queryResp, nil
}

func (c *PythonClient) HealthCheck() error {
	url := fmt.Sprintf("%s/health", c.baseURL)
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return fmt.Errorf("health check failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check returned status %d", resp.StatusCode)
	}

	return nil
}

// Handlers

func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, HealthResponse{
		Status:  "healthy",
		Service: "Legal RAG Backend API",
		Version: "1.0.0",
	})
}

func legalQueryHandler(pythonClient *PythonClient) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req LegalQueryRequest

		// Bind JSON request
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{
				Error:   "invalid_request",
				Message: fmt.Sprintf("Invalid request format: %v", err),
			})
			return
		}

		log.Printf("Received query: %s", req.Question)

		// Set defaults
		maxIterations := 3
		if req.MaxIterations != nil {
			maxIterations = *req.MaxIterations
		}

		topK := 3
		if req.TopK != nil {
			topK = *req.TopK
		}

		enableWebSearch := true
		if req.EnableWebSearch != nil {
			enableWebSearch = *req.EnableWebSearch
		}

		// Create Python request
		pythonReq := &PythonQueryRequest{
			Question:        req.Question,
			MaxIterations:   maxIterations,
			TopK:            topK,
			EnableWebSearch: enableWebSearch,
		}

		// Call Python AI Engine
		resp, err := pythonClient.Query(pythonReq)
		if err != nil {
			log.Printf("Error calling Python AI Engine: %v", err)
			c.JSON(http.StatusInternalServerError, ErrorResponse{
				Error:   "ai_engine_error",
				Message: fmt.Sprintf("Failed to process query: %v", err),
			})
			return
		}

		log.Printf("Query completed: %d iterations, %d internal results, %d web results",
			resp.Iterations, len(resp.SearchResults), len(resp.WebResults))

		// Return response
		c.JSON(http.StatusOK, resp)
	}
}

// Middleware
func loggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		method := c.Request.Method

		c.Next()

		duration := time.Since(start)
		statusCode := c.Writer.Status()

		log.Printf("%s %s - %d - %v", method, path, statusCode, duration)
	}
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

func main() {
	// Load configuration
	config := loadConfig()

	log.Printf("Starting Legal RAG Backend API")
	log.Printf("Server Port: %s", config.ServerPort)
	log.Printf("Python AI Engine URL: %s", config.PythonEngineURL)
	log.Printf("Request Timeout: %v", config.RequestTimeout)

	// Initialize Python client
	pythonClient := NewPythonClient(config.PythonEngineURL, config.RequestTimeout)

	// Check Python service health
	log.Printf("Checking Python AI Engine health...")
	if err := pythonClient.HealthCheck(); err != nil {
		log.Printf("WARNING: Python AI Engine health check failed: %v", err)
		log.Printf("Server will start anyway, but queries may fail")
	} else {
		log.Printf("✓ Python AI Engine is healthy")
	}

	// Setup Gin router
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(loggingMiddleware())
	router.Use(corsMiddleware())

	// Routes
	router.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "Legal RAG Backend API",
			"version": "1.0.0",
			"status":  "running",
		})
	})

	router.GET("/health", healthHandler)
	router.POST("/api/legal-query", legalQueryHandler(pythonClient))

	// Start server
	addr := fmt.Sprintf(":%s", config.ServerPort)
	log.Printf("Server listening on %s", addr)
	log.Printf("API Documentation: http://localhost:%s/", config.ServerPort)

	if err := router.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
