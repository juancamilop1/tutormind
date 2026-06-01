from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), default="student", nullable=False)
    career = Column(String(255), nullable=True)
    university = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cognitive_profile = relationship(
        "CognitiveProfile", back_populates="user", uselist=False
    )
    sessions = relationship("Session", back_populates="user")
    learning_events = relationship("LearningEvent", back_populates="user")
    students = relationship(
        "TeacherStudent",
        foreign_keys="TeacherStudent.teacher_id",
        back_populates="teacher",
    )
    teachers = relationship(
        "TeacherStudent",
        foreign_keys="TeacherStudent.student_id",
        back_populates="student",
    )


class TeacherStudent(Base):
    __tablename__ = "teacher_students"
    __table_args__ = (
        UniqueConstraint("teacher_id", "student_email", name="uq_teacher_student_email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    student_email = Column(String(255), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="students")
    student = relationship("User", foreign_keys=[student_id], back_populates="teachers")


class CognitiveProfile(Base):
    __tablename__ = "cognitive_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    learning_style = Column(String(50), default="unknown")
    preferred_session_length = Column(Integer, default=25)
    fatigue_threshold = Column(Integer, default=20)
    frustration_topics = Column(Text, default="[]")
    mastered_topics = Column(Text, default="[]")
    personality_type = Column(String(50), default="neutral")
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cognitive_profile")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(255), default="Nueva sesión")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0)
    topic_summary = Column(Text, nullable=True)

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", order_by="Message.timestamp")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    topic = Column(String(255), nullable=True)
    explanation_style = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="learning_events")
