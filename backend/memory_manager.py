import json
import re
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from models import CognitiveProfile, LearningEvent, Message, Session as ChatSession

SIGNAL_PATTERN = re.compile(
    r"\[SIGNAL:\s*event_type=(\w+),\s*topic=([^,\]]+),\s*style=([^\]]+)\]",
    re.IGNORECASE,
)

STYLE_ROTATION = [
    "analogies",
    "examples",
    "visual_descriptions",
    "structured_lists",
    "socratic",
    "narrative",
]


def get_conversation_history(db: Session, session_id: int, limit: int = 20) -> List[dict]:
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    messages = list(reversed(messages))
    return [{"role": m.role, "content": m.content} for m in messages]


def get_session_context(db: Session, user_id: int) -> str:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.started_at.desc())
        .limit(3)
        .all()
    )
    if not sessions:
        return ""

    parts = []
    for s in sessions:
        summary = s.topic_summary or s.subject or "Sin tema"
        parts.append(
            f"- Sesión '{s.subject}' ({s.message_count} mensajes): {summary}"
        )
    return "\n".join(parts)


def _parse_json_list(raw: Optional[str]) -> list:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save_json_list(items: list) -> str:
    return json.dumps(list(dict.fromkeys(items)), ensure_ascii=False)


def update_cognitive_profile(
    db: Session,
    user_id: int,
    event_type: str,
    topic: str,
    style: str,
) -> None:
    profile = (
        db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    )
    if not profile:
        return

    topic = (topic or "").strip()
    style = (style or "").strip()

    event = LearningEvent(
        user_id=user_id,
        event_type=event_type,
        topic=topic,
        explanation_style=style,
        timestamp=datetime.utcnow(),
    )
    db.add(event)

    frustration = _parse_json_list(profile.frustration_topics)
    mastered = _parse_json_list(profile.mastered_topics)

    if event_type == "mastered" and topic and topic not in mastered:
        mastered.append(topic)
        profile.mastered_topics = _save_json_list(mastered)

    if event_type == "frustrated" and topic and topic not in frustration:
        frustration.append(topic)
        profile.frustration_topics = _save_json_list(frustration)

    if event_type == "confused" and style:
        recent_confused = (
            db.query(LearningEvent)
            .filter(
                LearningEvent.user_id == user_id,
                LearningEvent.event_type == "confused",
                LearningEvent.explanation_style == style,
            )
            .order_by(LearningEvent.timestamp.desc())
            .limit(3)
            .all()
        )
        if len(recent_confused) >= 3:
            current = profile.learning_style or "unknown"
            if current in STYLE_ROTATION:
                idx = STYLE_ROTATION.index(current)
                next_style = STYLE_ROTATION[(idx + 1) % len(STYLE_ROTATION)]
            else:
                next_style = STYLE_ROTATION[0]
            profile.learning_style = next_style

    if event_type == "understood" and style and profile.learning_style == "unknown":
        profile.learning_style = style

    profile.last_updated = datetime.utcnow()
    db.commit()


def extract_and_update_signals(
    response_text: str, user_id: int, db: Session
) -> str:
    match = SIGNAL_PATTERN.search(response_text)
    if not match:
        return response_text

    event_type, topic, style = match.group(1), match.group(2).strip(), match.group(3).strip()
    update_cognitive_profile(db, user_id, event_type.lower(), topic, style)
    clean = SIGNAL_PATTERN.sub("", response_text).rstrip()
    return clean
