import json
from datetime import datetime
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from gemini_client import stream_chat
from memory_manager import (
    extract_and_update_signals,
    get_conversation_history,
    get_session_context,
)
from models import CognitiveProfile, Message, Session as ChatSession, User
from prompt_builder import build_system_prompt
from schemas import (
    ChatMessageRequest,
    ExamGenerateRequest,
    ExamGenerateResponse,
    ExamQuestion,
    ExamSubmitRequest,
    ExamSubmitResponse,
    MessageResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SIGNAL_START = "[SIGNAL:"


def _collect_stream_text(system_prompt: str, history: list[dict], user_message: str) -> str:
    full = ""
    for chunk in stream_chat(system_prompt, history, user_message):
        full += chunk
    return full.strip()


def _safe_yield_text(accumulated: str, previously_yielded: str) -> tuple[str, str]:
    idx = accumulated.find(SIGNAL_START)
    if idx >= 0:
        safe = accumulated[:idx]
    else:
        hold = 0
        for i in range(1, len(SIGNAL_START) + 1):
            if accumulated.endswith(SIGNAL_START[:i]):
                hold = i
                break
        safe = accumulated[:-hold] if hold else accumulated
    new_part = safe[len(previously_yielded) :]
    return new_part, safe


def _sse_generator(
    user_id: int,
    session_id: int,
    message: str,
) -> Generator[str, None, None]:
    db = SessionLocal()
    try:
        yield from _sse_generator_body(db, user_id, session_id, message)
    finally:
        db.close()


def _sse_generator_body(
    db: Session,
    user_id: int,
    session_id: int,
    message: str,
) -> Generator[str, None, None]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        yield f"event: stream-error\ndata: {json.dumps('Usuario no encontrado')}\n\n"
        return

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        yield f"event: stream-error\ndata: {json.dumps('Sesión no encontrada')}\n\n"
        return

    profile = (
        db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    )
    if not profile:
        yield f"event: stream-error\ndata: {json.dumps('Perfil no encontrado')}\n\n"
        return

    session_context = get_session_context(db, user_id)
    system_prompt = build_system_prompt(
        user,
        profile,
        session_context,
        message_count=session.message_count or 0,
        session_subject=session.subject or "",
    )
    history = get_conversation_history(db, session_id)

    user_msg = Message(
        session_id=session_id,
        role="user",
        content=message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_msg)
    session.message_count = (session.message_count or 0) + 1
    db.commit()

    accumulated = ""
    yielded_safe = ""

    try:
        for chunk in stream_chat(system_prompt, history, message):
            accumulated += chunk
            new_part, yielded_safe = _safe_yield_text(accumulated, yielded_safe)
            if new_part:
                yield f"data: {json.dumps(new_part)}\n\n"

        clean = extract_and_update_signals(accumulated, user_id, db)
        final_part, _ = _safe_yield_text(clean, yielded_safe)
        if final_part:
            yield f"data: {json.dumps(final_part)}\n\n"

        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content=clean,
            timestamp=datetime.utcnow(),
        )
        db.add(assistant_msg)
        session.message_count = (session.message_count or 0) + 1
        db.commit()

        yield "event: done\ndata: {}\n\n"
    except Exception as exc:
        detail = str(exc)
        if getattr(exc, "__cause__", None):
            detail = f"{detail} Causa: {exc.__cause__}"
        yield f"event: stream-error\ndata: {json.dumps(detail)}\n\n"


def _streaming_response(user_id: int, session_id: int, message: str) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(user_id, session_id, message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{user_id}/message")
async def send_message(user_id: int, payload: ChatMessageRequest):
    return _streaming_response(user_id, payload.session_id, payload.message)


@router.get("/{user_id}/message")
async def send_message_sse(
    user_id: int,
    message: str = Query(...),
    session_id: int = Query(...),
):
    """GET variant for EventSource clients."""
    return _streaming_response(user_id, session_id, message)


@router.post("/{user_id}/session", response_model=SessionResponse)
def create_session(
    user_id: int,
    payload: SessionCreate,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Close any open session for this user so stats can segment by session window.
    open_sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id, ChatSession.ended_at.is_(None))
        .all()
    )
    now = datetime.utcnow()
    for s in open_sessions:
        s.ended_at = now

    session = ChatSession(
        user_id=user_id,
        subject=payload.subject or "Nueva sesión",
        started_at=now,
        message_count=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{user_id}/sessions", response_model=list[SessionResponse])
def list_sessions(user_id: int, db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.started_at.desc())
        .all()
    )
    return sessions


@router.patch("/{user_id}/session/{session_id}", response_model=SessionResponse)
def update_session(
    user_id: int,
    session_id: int,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if payload.subject is not None:
        session.subject = payload.subject
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{user_id}/session/{session_id}")
def delete_session(
    user_id: int,
    session_id: int,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    db.query(Message).filter(Message.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.get("/{user_id}/session/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(
    user_id: int,
    session_id: int,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp.asc())
        .all()
    )


@router.post("/{user_id}/exam/generate", response_model=ExamGenerateResponse)
def generate_exam(
    user_id: int,
    payload: ExamGenerateRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    profile = db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    q_count = max(3, min(10, payload.question_count))
    session_context = get_session_context(db, user_id)
    system_prompt = build_system_prompt(user, profile, session_context, message_count=0)
    instructions = (
        f"Genera un mini parcial TIPO TEST de {q_count} preguntas para {user.name} basado en los temas "
        "estudiados en sesiones recientes. Formato estricto JSON con: "
        '{"title":"...","instructions":"...","questions":[{"id":1,"question":"...","options":["A","B","C","D"],"correct_index":1,"explanation":"..."}]}. '
        "Reglas: options siempre de 4 elementos, correct_index entre 0 y 3, explanation corta y clara. "
        "No incluyas markdown ni texto extra."
    )
    raw = _collect_stream_text(system_prompt, [], instructions)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="No se pudo generar el parcial en formato válido."
        )

    questions = parsed.get("questions") or []
    cleaned_questions: list[ExamQuestion] = []
    for i, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            continue
        text = str(q.get("question", "")).strip()
        options = q.get("options") if isinstance(q.get("options"), list) else []
        options = [str(opt).strip() for opt in options if str(opt).strip()]
        if len(options) != 4 or not text:
            continue
        try:
            correct_index = int(q.get("correct_index", 0))
        except Exception:
            correct_index = 0
        correct_index = max(0, min(3, correct_index))
        explanation = str(q.get("explanation", "")).strip() or "Revisa la idea central del tema."
        cleaned_questions.append(
            ExamQuestion(
                id=i,
                question=text,
                options=options,
                correct_index=correct_index,
                explanation=explanation,
            )
        )
    if not cleaned_questions:
        raise HTTPException(status_code=500, detail="No se generaron preguntas del parcial.")

    return ExamGenerateResponse(
        title=parsed.get("title", "Parcial personalizado TutorMind"),
        instructions=parsed.get(
            "instructions", "Responde cada pregunta con claridad. Se evaluará comprensión."
        ),
        questions=cleaned_questions,
    )


@router.post("/{user_id}/exam/submit", response_model=ExamSubmitResponse)
def submit_exam(
    user_id: int,
    payload: ExamSubmitRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    profile = db.query(CognitiveProfile).filter(CognitiveProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    if not payload.selected_indexes:
        raise HTTPException(status_code=400, detail="Debes enviar respuestas para evaluar.")
    # Kept for compatibility. Frontend now validates locally with answer key.
    score = 0
    feedback = "Evaluación local habilitada en frontend."
    return ExamSubmitResponse(score=score, feedback=feedback, results=[])
