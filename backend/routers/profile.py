import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import CognitiveProfile, LearningEvent, Message, Session as ChatSession
from schemas import CognitiveProfileResponse, CognitiveProfileUpdate, UserStatsResponse

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _to_response(profile: CognitiveProfile) -> CognitiveProfileResponse:
    return CognitiveProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        learning_style=profile.learning_style,
        preferred_session_length=profile.preferred_session_length,
        fatigue_threshold=profile.fatigue_threshold,
        frustration_topics=json.loads(profile.frustration_topics or "[]"),
        mastered_topics=json.loads(profile.mastered_topics or "[]"),
        personality_type=profile.personality_type,
        last_updated=profile.last_updated,
    )


@router.get("/{user_id}", response_model=CognitiveProfileResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = (
        db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return _to_response(profile)


@router.patch("/{user_id}", response_model=CognitiveProfileResponse)
def update_profile(
    user_id: int,
    payload: CognitiveProfileUpdate,
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "frustration_topics" in data and data["frustration_topics"] is not None:
        data["frustration_topics"] = json.dumps(
            data["frustration_topics"], ensure_ascii=False
        )
    if "mastered_topics" in data and data["mastered_topics"] is not None:
        data["mastered_topics"] = json.dumps(
            data["mastered_topics"], ensure_ascii=False
        )

    for key, value in data.items():
        setattr(profile, key, value)
    profile.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _to_response(profile)


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
def get_profile_stats(
    user_id: int,
    session_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    total_sessions = (
        db.query(func.count(ChatSession.id)).filter(ChatSession.user_id == user_id).scalar()
        or 0
    )
    session = None
    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

    message_query = db.query(func.count(Message.id)).join(
        ChatSession, Message.session_id == ChatSession.id
    )
    if session is not None:
        message_query = message_query.filter(ChatSession.id == session.id)
    else:
        message_query = message_query.filter(ChatSession.user_id == user_id)
    total_messages = message_query.scalar() or 0

    event_base = db.query(func.count(LearningEvent.id)).filter(
        LearningEvent.user_id == user_id
    )
    if session is not None:
        start = session.started_at
        next_session = (
            db.query(ChatSession)
            .filter(
                ChatSession.user_id == user_id,
                ChatSession.started_at > session.started_at,
            )
            .order_by(ChatSession.started_at.asc())
            .first()
        )
        end = next_session.started_at if next_session else (session.ended_at or datetime.utcnow())
        event_base = event_base.filter(
            LearningEvent.timestamp >= start, LearningEvent.timestamp <= end
        )

    understood_events = (
        event_base.filter(LearningEvent.event_type == "understood").scalar() or 0
    )
    confused_events = event_base.filter(LearningEvent.event_type == "confused").scalar() or 0
    frustrated_events = (
        event_base.filter(LearningEvent.event_type == "frustrated").scalar() or 0
    )
    mastered_events = event_base.filter(LearningEvent.event_type == "mastered").scalar() or 0

    mastered_topics = json.loads(profile.mastered_topics or "[]")
    denominator = max(1, understood_events + confused_events + frustrated_events)
    understanding_score = int(
        max(0, min(100, ((understood_events + mastered_events) / denominator) * 100))
    )

    return UserStatsResponse(
        total_sessions=total_sessions,
        total_messages=total_messages,
        mastered_topics_count=len(mastered_topics),
        confused_events=confused_events,
        understood_events=understood_events,
        frustrated_events=frustrated_events,
        mastered_events=mastered_events,
        understanding_score=understanding_score,
    )
