from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: Literal["student", "teacher"] = "student"
    career: Optional[str] = None
    university: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class CognitiveProfileResponse(BaseModel):
    id: int
    user_id: int
    learning_style: str
    preferred_session_length: int
    fatigue_threshold: int
    frustration_topics: list[str]
    mastered_topics: list[str]
    personality_type: str
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    career: Optional[str] = None
    university: Optional[str] = None
    created_at: Optional[datetime] = None
    cognitive_profile: Optional[CognitiveProfileResponse] = None

    class Config:
        from_attributes = True


class CognitiveProfileUpdate(BaseModel):
    learning_style: Optional[str] = None
    preferred_session_length: Optional[int] = None
    fatigue_threshold: Optional[int] = None
    frustration_topics: Optional[list[str]] = None
    mastered_topics: Optional[list[str]] = None
    personality_type: Optional[str] = None


class SessionCreate(BaseModel):
    subject: Optional[str] = "Nueva sesión"


class SessionUpdate(BaseModel):
    subject: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    message_count: int
    topic_summary: Optional[str] = None

    class Config:
        from_attributes = True


class ChatMessageRequest(BaseModel):
    message: str
    session_id: int


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class BarChartItem(BaseModel):
    label: str
    value: int
    tone: str = "primary"


class TopicInsight(BaseModel):
    topic: str
    understood: int
    confused: int
    frustrated: int
    mastered: int
    status: str
    summary: str


class UserStatsResponse(BaseModel):
    total_sessions: int
    total_messages: int
    mastered_topics_count: int
    confused_events: int
    understood_events: int
    frustrated_events: int
    mastered_events: int
    understanding_score: int
    event_bars: list[BarChartItem]
    topic_insights: list[TopicInsight]
    learning_summary: str


class ExamQuestion(BaseModel):
    id: int
    question: str
    options: list[str]
    correct_index: int
    explanation: str


class ExamGenerateResponse(BaseModel):
    title: str
    instructions: str
    questions: list[ExamQuestion]


class ExamGenerateRequest(BaseModel):
    session_id: Optional[int] = None
    question_count: int = 5


class ExamSubmitRequest(BaseModel):
    session_id: Optional[int] = None
    selected_indexes: list[int]


class ExamSubmitResponse(BaseModel):
    score: int
    feedback: str
    results: list[bool]


class TeacherAddStudent(BaseModel):
    email: EmailStr


class TeacherStudentResponse(BaseModel):
    id: int
    student_id: Optional[int] = None
    student_email: str
    student_name: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class StudentOverview(BaseModel):
    enrollment_id: int
    student_id: Optional[int] = None
    student_email: str
    student_name: Optional[str] = None
    status: str
    learning_style: str
    learning_style_label: str
    total_sessions: int
    total_messages: int
    event_bars: list[BarChartItem]
    topic_insights: list[TopicInsight]
    learning_summary: str
