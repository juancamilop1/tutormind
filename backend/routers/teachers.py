import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from analytics import build_event_bars, build_learning_summary, build_topic_insights
from database import get_db
from models import CognitiveProfile, LearningEvent, Message, Session as ChatSession, TeacherStudent, User
from schemas import (
    StudentOverview,
    TeacherAddStudent,
    TeacherStudentResponse,
)

router = APIRouter(prefix="/api/teachers", tags=["teachers"])

STYLE_LABELS = {
    "analogies": "Aprende con analogías",
    "examples": "Aprende con ejemplos",
    "visual_descriptions": "Aprende visualmente",
    "structured_lists": "Aprende con listas estructuradas",
    "socratic": "Método socrático",
    "narrative": "Aprende con narrativas",
    "unknown": "Estilo en detección",
}


def _get_teacher(teacher_id: int, db: Session) -> User:
    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    if teacher.role != "teacher":
        raise HTTPException(status_code=403, detail="Solo profesores pueden acceder")
    return teacher


def _student_stats(db: Session, student_id: int) -> dict[str, int]:
    understood = (
        db.query(func.count(LearningEvent.id))
        .filter(LearningEvent.user_id == student_id, LearningEvent.event_type == "understood")
        .scalar()
        or 0
    )
    confused = (
        db.query(func.count(LearningEvent.id))
        .filter(LearningEvent.user_id == student_id, LearningEvent.event_type == "confused")
        .scalar()
        or 0
    )
    frustrated = (
        db.query(func.count(LearningEvent.id))
        .filter(LearningEvent.user_id == student_id, LearningEvent.event_type == "frustrated")
        .scalar()
        or 0
    )
    mastered = (
        db.query(func.count(LearningEvent.id))
        .filter(LearningEvent.user_id == student_id, LearningEvent.event_type == "mastered")
        .scalar()
        or 0
    )
    return {
        "understood": understood,
        "confused": confused,
        "frustrated": frustrated,
        "mastered": mastered,
    }


def _build_student_overview(db: Session, enrollment: TeacherStudent) -> StudentOverview:
    student = enrollment.student
    profile = None
    if student:
        profile = (
            db.query(CognitiveProfile)
            .filter(CognitiveProfile.user_id == student.id)
            .first()
        )

    if not student or not profile:
        return StudentOverview(
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            student_email=enrollment.student_email,
            student_name=student.name if student else None,
            status=enrollment.status,
            learning_style="unknown",
            learning_style_label=STYLE_LABELS["unknown"],
            total_sessions=0,
            total_messages=0,
            event_bars=build_event_bars(0, 0, 0, 0),
            topic_insights=[],
            learning_summary=(
                "El estudiante aún no se ha registrado. "
                "Cuando cree su cuenta con este correo, verás su progreso aquí."
            ),
        )

    counts = _student_stats(db, student.id)
    topic_insights = build_topic_insights(db, student.id, profile)
    total_sessions = (
        db.query(func.count(ChatSession.id))
        .filter(ChatSession.user_id == student.id)
        .scalar()
        or 0
    )
    total_messages = (
        db.query(func.count(Message.id))
        .join(ChatSession, Message.session_id == ChatSession.id)
        .filter(ChatSession.user_id == student.id)
        .scalar()
        or 0
    )

    return StudentOverview(
        enrollment_id=enrollment.id,
        student_id=student.id,
        student_email=student.email,
        student_name=student.name,
        status=enrollment.status,
        learning_style=profile.learning_style,
        learning_style_label=STYLE_LABELS.get(profile.learning_style, STYLE_LABELS["unknown"]),
        total_sessions=total_sessions,
        total_messages=total_messages,
        event_bars=build_event_bars(
            counts["understood"],
            counts["confused"],
            counts["frustrated"],
            counts["mastered"],
        ),
        topic_insights=topic_insights,
        learning_summary=build_learning_summary(profile, counts, topic_insights),
    )


@router.get("/{teacher_id}/students", response_model=list[StudentOverview])
def list_students(teacher_id: int, db: Session = Depends(get_db)):
    _get_teacher(teacher_id, db)
    enrollments = (
        db.query(TeacherStudent)
        .options(joinedload(TeacherStudent.student).joinedload(User.cognitive_profile))
        .filter(TeacherStudent.teacher_id == teacher_id)
        .order_by(TeacherStudent.created_at.desc())
        .all()
    )
    return [_build_student_overview(db, enrollment) for enrollment in enrollments]


@router.post("/{teacher_id}/students", response_model=TeacherStudentResponse)
def add_student(
    teacher_id: int,
    payload: TeacherAddStudent,
    db: Session = Depends(get_db),
):
    _get_teacher(teacher_id, db)
    email = payload.email.strip().lower()

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if teacher and teacher.email.lower() == email:
        raise HTTPException(status_code=400, detail="No puedes agregarte a ti mismo")

    existing = (
        db.query(TeacherStudent)
        .filter(
            TeacherStudent.teacher_id == teacher_id,
            func.lower(TeacherStudent.student_email) == email,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Este estudiante ya está en tu lista")

    student = db.query(User).filter(func.lower(User.email) == email).first()
    if student and student.role == "teacher":
        raise HTTPException(status_code=400, detail="No puedes agregar a otro profesor")

    enrollment = TeacherStudent(
        teacher_id=teacher_id,
        student_id=student.id if student else None,
        student_email=email,
        status="active" if student else "pending",
        created_at=datetime.utcnow(),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return TeacherStudentResponse(
        id=enrollment.id,
        student_id=enrollment.student_id,
        student_email=enrollment.student_email,
        student_name=student.name if student else None,
        status=enrollment.status,
        created_at=enrollment.created_at,
    )


@router.delete("/{teacher_id}/students/{enrollment_id}")
def remove_student(teacher_id: int, enrollment_id: int, db: Session = Depends(get_db)):
    _get_teacher(teacher_id, db)
    enrollment = (
        db.query(TeacherStudent)
        .filter(
            TeacherStudent.id == enrollment_id,
            TeacherStudent.teacher_id == teacher_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado en tu lista")
    db.delete(enrollment)
    db.commit()
    return {"ok": True}
