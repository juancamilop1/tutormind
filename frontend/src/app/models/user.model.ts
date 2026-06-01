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
  role: 'student' | 'teacher';
  career?: string;
  university?: string;
  created_at?: string;
  cognitive_profile?: CognitiveProfile;
}

export interface BarChartItem {
  label: string;
  value: number;
  tone: 'success' | 'warning' | 'danger' | 'primary';
}

export interface TopicInsight {
  topic: string;
  understood: number;
  confused: number;
  frustrated: number;
  mastered: number;
  status: 'dominado' | 'aprendiendo' | 'con_dificultad' | 'explorando';
  summary: string;
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
  event_bars: BarChartItem[];
  topic_insights: TopicInsight[];
  learning_summary: string;
}

export interface StudentOverview {
  enrollment_id: number;
  student_id?: number | null;
  student_email: string;
  student_name?: string | null;
  status: string;
  learning_style: string;
  learning_style_label: string;
  total_sessions: number;
  total_messages: number;
  event_bars: BarChartItem[];
  topic_insights: TopicInsight[];
  learning_summary: string;
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
