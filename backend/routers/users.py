import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from auth_utils import hash_password, verify_password
from database import get_db
from models import CognitiveProfile, TeacherStudent, User
from schemas import CognitiveProfileResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])

STYLE_LABELS = {
    "analogies": "Aprende con analogías",
    "examples": "Aprende con ejemplos",
    "visual_descriptions": "Aprende visualmente",
    "structured_lists": "Aprende con listas estructuradas",
    "socratic": "Método socrático",
    "narrative": "Aprende con narrativas",
    "unknown": "Estilo en detección",
}


def _profile_to_response(profile: CognitiveProfile) -> CognitiveProfileResponse:
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


def _user_to_response(user: User) -> UserResponse:
    profile = None
    if user.cognitive_profile:
        profile = _profile_to_response(user.cognitive_profile)
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role or "student",
        career=user.career,
        university=user.university,
        created_at=user.created_at,
        cognitive_profile=profile,
    )


def _link_pending_teacher_enrollments(db: Session, user: User) -> None:
    pending = (
        db.query(TeacherStudent)
        .filter(
            func.lower(TeacherStudent.student_email) == user.email.lower(),
            TeacherStudent.student_id.is_(None),
        )
        .all()
    )
    for enrollment in pending:
        enrollment.student_id = user.id
        enrollment.status = "active"
    if pending:
        db.commit()


@router.post("", response_model=UserResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        career=payload.career,
        university=payload.university,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    if user.role == "student":
        profile = CognitiveProfile(user_id=user.id)
        db.add(profile)

    db.commit()
    db.refresh(user)
    _link_pending_teacher_enrollments(db, user)

    user = (
        db.query(User)
        .options(joinedload(User.cognitive_profile))
        .filter(User.id == user.id)
        .first()
    )
    return _user_to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.cognitive_profile))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _user_to_response(user)


@router.post("/login", response_model=UserResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = (
        db.query(User)
        .options(joinedload(User.cognitive_profile))
        .filter(func.lower(User.email) == email)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Tu cuenta no tiene contraseña. Crea una cuenta nueva.",
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return _user_to_response(user)
