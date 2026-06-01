# TutorMind AI

Chatbot educativo adaptativo para estudiantes universitarios. Aprende tu estilo cognitivo y adapta cada explicación en tiempo real.

## Stack

- **Frontend:** Angular 17+ (standalone components)
- **Backend:** Python + FastAPI
- **IA:** Google Gemini (`gemini-1.5-pro`)
- **Base de datos:** SQLite + SQLAlchemy
- **Streaming:** Server-Sent Events (SSE) 

## Estructura

```
tutormind/
├── backend/          # API FastAPI
├── frontend/         # App Angular
├── .env.example      # Plantilla de variables (sí se sube a GitHub)
├── .env              # Tus claves reales (solo local, en .gitignore)
└── README.md
```

## Requisitos

- Python 3.10+
- Node.js 18+
- API key de [Google AI Studio](https://aistudio.google.com/app/apikey)

## Configuración

1. Copia la plantilla y edita tus claves (el archivo `.env` no se sube al repositorio):

```bash
cp .env.example .env
```

2. Edita `.env` en la raíz del proyecto:

```env
GEMINI_API_KEY=tu_clave_aqui
DATABASE_URL=sqlite:///./tutormind.db
ALLOWED_ORIGINS=http://localhost:4200
```

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

La API estará en `http://localhost:8000`. Documentación interactiva: `http://localhost:8000/docs`.

## Frontend

```bash
cd frontend
npm install
npm start
```

Abre `http://localhost:4200`.

## Flujo de uso

1. Completa el onboarding (nombre, email, carrera, universidad).
2. Crea o selecciona una sesión de estudio.
3. Escribe preguntas; las respuestas llegan en streaming por SSE.
4. El perfil cognitivo se actualiza silenciosamente tras cada respuesta (señales `[SIGNAL:...]` procesadas en el backend).

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/users` | Crear usuario |
| POST | `/api/users/login` | Login por email |
| GET | `/api/profile/{user_id}` | Perfil cognitivo |
| POST | `/api/chat/{user_id}/session` | Nueva sesión |
| GET | `/api/chat/{user_id}/message` | Chat SSE (EventSource) |
| POST | `/api/chat/{user_id}/message` | Chat SSE (alternativa POST) |

## Notas

- Sin contraseña por ahora; el login es solo por email.
- Coloca la base de datos ejecutando uvicorn desde la carpeta `backend`.
- Si Gemini no responde, verifica `GEMINI_API_KEY` en `.env`.
