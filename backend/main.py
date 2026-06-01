import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(__file__))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import Base, engine, run_migrations
from routers import chat, profile, teachers, users

run_migrations()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TutorMind AI", version="1.0.0")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(teachers.router)
app.include_router(chat.router)
app.include_router(profile.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TutorMind AI"}


@app.get("/")
def root():
    return {
        "service": "TutorMind AI",
        "docs": "/docs",
        "health": "/api/health",
        "message": "API activa. Usa el frontend en http://localhost:4200",
    }
