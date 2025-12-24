import { useState, useCallback } from 'react';
import { queryLegalRAG, type LegalQueryRequest, type LegalQueryResponse } from '../api/service';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: Partial<LegalQueryResponse>;
  isLoading?: boolean;
}

export const useChatStore = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = useCallback(async (question: string, options: Partial<LegalQueryRequest> = {}) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    const assistantMsgId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const result = await queryLegalRAG({
        question,
        ...options,
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: result.answer,
                isLoading: false,
                metadata: result,
              }
            : msg
        )
      );
    } catch (error) {
      console.error('Error querying Legal RAG:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: 'Xin lỗi, đã có lỗi xảy ra trong quá trình xử lý câu hỏi của bạn. Vui lòng kiểm tra kết nối với backend.',
                isLoading: false,
              }
            : msg
        )
      );
    } finally {
      setIsTyping(false);
    }
  }, []);

  return {
    messages,
    isTyping,
    sendMessage,
    setMessages,
  };
};
