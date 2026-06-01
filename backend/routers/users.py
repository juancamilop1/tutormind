import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import CognitiveProfile, User
from schemas import CognitiveProfileResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


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
        career=user.career,
        university=user.university,
        created_at=user.created_at,
        cognitive_profile=profile,
    )


@router.post("", response_model=UserResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        name=payload.name,
        email=payload.email,
        career=payload.career,
        university=payload.university,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    profile = CognitiveProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
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
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _user_to_response(user)
