export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
  game_context: string;
  session_id?: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  messages?: Message[];
} 