import os
import re
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_api_key = os.getenv("GEMINI_API_KEY")
if _api_key:
    genai.configure(api_key=_api_key)

# Free-tier friendly defaults
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# For free tier, keep this restricted to Flash models only.
ALLOWED_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_ALLOWED_MODELS",
        "gemini-1.5-flash,gemini-1.5-flash-8b",
    ).split(",")
    if m.strip()
]

FALLBACK_MODELS = ALLOWED_MODELS[:]  # retry within allowed list


def _map_role(role: str) -> str:
    if role == "assistant":
        return "model"
    return "user"


def _build_history(conversation_history: List[Dict[str, Any]]) -> list:
    history = []
    for msg in conversation_history:
        role = _map_role(msg.get("role", "user"))
        content = msg.get("content") or msg.get("parts", "")
        if isinstance(content, list):
            content = content[0] if content else ""
        history.append({"role": role, "parts": [str(content)]})
    return history


def _list_generate_models() -> Set[str]:
    names: Set[str] = set()
    try:
        for model in genai.list_models():
            methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                raw_name = getattr(model, "name", "") or ""
                names.add(raw_name.replace("models/", ""))
    except Exception:
        # If listing fails, we still try hardcoded fallbacks.
        return set()
    return names


def _resolve_models_to_try() -> List[str]:
    preferred = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    available = _list_generate_models()
    if not available:
        return preferred

    allowed = set(ALLOWED_MODELS) if ALLOWED_MODELS else set(preferred)
    filtered = [m for m in preferred if m in available and m in allowed]
    if filtered:
        return filtered

    # Last resort: pick any *allowed* available model that supports generation.
    last_resort = [m for m in available if m in allowed]
    return last_resort or preferred


def _try_extract_retry_delay_seconds(err_text: str) -> Optional[int]:
    # Example: "Please retry in 9.4685s." or "retry_delay { seconds: 9 }"
    m = re.search(r"Please retry in\s+(\d+)", err_text)
    if m:
        return int(m.group(1))
    m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", err_text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _is_quota_error(err_text: str) -> bool:
    t = err_text.lower()
    return "exceeded your current quota" in t or "quota exceeded" in t or "429" in t


def stream_chat(
    system_prompt: str,
    conversation_history: List[Dict[str, Any]],
    user_message: str,
) -> Generator[str, None, None]:
    """Stream text chunks from Gemini for the given conversation."""
    if not _api_key:
        raise RuntimeError(
            "GEMINI_API_KEY no configurada. Añade tu clave en el archivo .env"
        )

    history = _build_history(conversation_history)
    models_to_try = _resolve_models_to_try()
    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )
            chat = model.start_chat(history=history)
            response = chat.send_message(user_message, stream=True)

            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as exc:
            last_error = exc
            continue

    # Friendly error for quota/rate limits (very common on free tier).
    err_text = str(last_error) if last_error else "Error desconocido"
    if _is_quota_error(err_text):
        retry_s = _try_extract_retry_delay_seconds(err_text)
        if "limit: 0" in err_text:
            raise RuntimeError(
                "Tu cuota FREE de Gemini para este proyecto está en 0 (no habilitada o agotada). "
                "Solución: usa otra API key/proyecto con cuota activa o habilita facturación en Google Cloud."
            ) from last_error
        if retry_s is not None:
            raise RuntimeError(
                f"Gemini te rate-limitó (HTTP 429). Espera ~{retry_s}s y reintenta."
            ) from last_error
        raise RuntimeError(
            "Gemini te rate-limitó (HTTP 429). Espera unos segundos y reintenta."
        ) from last_error

    raise RuntimeError(
        "No se pudo generar respuesta con los modelos disponibles de Gemini."
    ) from last_error
