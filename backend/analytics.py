import json
from collections import defaultdict

from sqlalchemy.orm import Session

from models import CognitiveProfile, LearningEvent
from schemas import BarChartItem, TopicInsight


def _topic_status(
    topic: str,
    mastered_topics: set[str],
    counts: dict[str, int],
) -> tuple[str, str]:
    if topic in mastered_topics:
        return "dominado", "El estudiante domina este tema."

    frustrated = counts.get("frustrated", 0)
    confused = counts.get("confused", 0)
    understood = counts.get("understood", 0)
    mastered = counts.get("mastered", 0)

    if frustrated >= 2 or (confused >= 3 and understood == 0):
        return (
            "con_dificultad",
            "Muestra dificultad recurrente; conviene reforzar con ejemplos y práctica guiada.",
        )
    if understood >= 2 or mastered >= 1:
        return (
            "aprendiendo",
            "Está avanzando y muestra señales de comprensión, pero aún no lo domina por completo.",
        )
    return (
        "explorando",
        "Acaba de empezar con este tema; aún se están recopilando señales de aprendizaje.",
    )


def build_topic_insights(
    db: Session,
    user_id: int,
    profile: CognitiveProfile,
) -> list[TopicInsight]:
    mastered_topics = set(json.loads(profile.mastered_topics or "[]"))
    frustration_topics = json.loads(profile.frustration_topics or "[]")

    events = (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == user_id, LearningEvent.topic.isnot(None))
        .all()
    )

    by_topic: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "understood": 0,
            "confused": 0,
            "frustrated": 0,
            "mastered": 0,
        }
    )
    for event in events:
        topic = (event.topic or "").strip()
        if not topic:
            continue
        key = event.event_type
        if key in by_topic[topic]:
            by_topic[topic][key] += 1

    topics = set(frustration_topics) | mastered_topics | set(by_topic.keys())
    insights: list[TopicInsight] = []

    for topic in sorted(topics):
        counts = by_topic.get(topic, {})
        status, summary = _topic_status(topic, mastered_topics, counts)
        insights.append(
            TopicInsight(
                topic=topic,
                understood=counts.get("understood", 0),
                confused=counts.get("confused", 0),
                frustrated=counts.get("frustrated", 0),
                mastered=counts.get("mastered", 0),
                status=status,
                summary=summary,
            )
        )

    return insights


def build_event_bars(
    understood: int,
    confused: int,
    frustrated: int,
    mastered: int,
) -> list[BarChartItem]:
    return [
        BarChartItem(label="Entendió", value=understood, tone="success"),
        BarChartItem(label="Confusión", value=confused, tone="warning"),
        BarChartItem(label="Frustración", value=frustrated, tone="danger"),
        BarChartItem(label="Dominado", value=mastered, tone="primary"),
    ]


def build_learning_summary(
    profile: CognitiveProfile,
    stats_counts: dict[str, int],
    topic_insights: list[TopicInsight],
) -> str:
    style = profile.learning_style or "unknown"
    style_map = {
        "analogies": "analogías",
        "examples": "ejemplos concretos",
        "visual_descriptions": "descripciones visuales",
        "structured_lists": "listas estructuradas",
        "socratic": "preguntas guiadas",
        "narrative": "narrativas",
        "unknown": "un estilo aún en detección",
    }
    style_label = style_map.get(style, style_map["unknown"])

    mastered = [t.topic for t in topic_insights if t.status == "dominado"]
    struggling = [t.topic for t in topic_insights if t.status == "con_dificultad"]
    learning = [t.topic for t in topic_insights if t.status == "aprendiendo"]

    parts = [f"Aprende mejor con {style_label}."]
    if learning:
        parts.append(f"Está aprendiendo activamente: {', '.join(learning[:3])}.")
    if mastered:
        parts.append(f"Ya domina: {', '.join(mastered[:3])}.")
    if struggling:
        parts.append(f"Necesita apoyo en: {', '.join(struggling[:3])}.")
    if stats_counts.get("understood", 0) + stats_counts.get("mastered", 0) > stats_counts.get(
        "frustrated", 0
    ):
        parts.append("La tendencia general es positiva.")
    elif stats_counts.get("frustrated", 0) > 0:
        parts.append("Hay señales de frustración; conviene revisar esos temas.")

    return " ".join(parts)
