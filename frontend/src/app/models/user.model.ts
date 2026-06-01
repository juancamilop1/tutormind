export interface CognitiveProfile {
  id: number;
  user_id: number;
  learning_style: string;
  preferred_session_length: number;
  fatigue_threshold: number;
  frustration_topics: string[];
  mastered_topics: string[];
  personality_type: string;
  last_updated?: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  career?: string;
  university?: string;
  created_at?: string;
  cognitive_profile?: CognitiveProfile;
}

export interface ChatSession {
  id: number;
  user_id: number;
  subject: string;
  started_at?: string;
  ended_at?: string;
  message_count: number;
  topic_summary?: string;
}

export interface ChatMessage {
  id?: number;
  session_id?: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  streaming?: boolean;
}

export interface UserStats {
  total_sessions: number;
  total_messages: number;
  mastered_topics_count: number;
  confused_events: number;
  understood_events: number;
  frustrated_events: number;
  mastered_events: number;
  understanding_score: number;
}

export interface ExamQuestion {
  id: number;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface ExamGenerateResponse {
  title: string;
  instructions: string;
  questions: ExamQuestion[];
}

export interface ExamSubmitResponse {
  score: number;
  feedback: string;
}
