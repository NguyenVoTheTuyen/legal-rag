import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface LegalQueryRequest {
  question: string;
  max_iterations?: number;
  top_k?: number;
  enable_web_search?: boolean;
}

export interface LegalQueryResponse {
  answer: string;
  search_results: Array<{
    title: string;
    content: string;
    score: number;
    metadata?: Record<string, any>;
  }>;
  web_results: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  iterations: number;
  query_used: string;
}

export const queryLegalRAG = async (data: LegalQueryRequest): Promise<LegalQueryResponse> => {
  const response = await api.post<LegalQueryResponse>('/api/legal-query', data);
  return response.data;
};

export const checkBackendHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.status === 200;
  } catch (error) {
    return false;
  }
};
