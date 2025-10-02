from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Iterable, List

from .models import Exercise, WorkoutSession


FOCUS_GROUPS = {
    "Pecho": {"group": "upper", "suggestions": ["Press de banca", "Fondos", "Press inclinado"]},
    "Espalda": {"group": "upper", "suggestions": ["Dominadas", "Remo con barra", "Peso muerto" ]},
    "Piernas": {"group": "lower", "suggestions": ["Sentadillas", "Prensa", "Peso muerto rumano"]},
    "Hombros": {"group": "upper", "suggestions": ["Press militar", "Elevaciones laterales"]},
    "Brazos": {"group": "upper", "suggestions": ["Curl con barra", "Fondos en paralelas", "Extensión de tríceps"]},
    "Core": {"group": "core", "suggestions": ["Plancha", "Crunches", "Levantamiento de piernas"]},
}


def summarize_recent_sessions(sessions: Iterable[WorkoutSession]) -> Counter[str]:
    focuses: Counter[str] = Counter()
    for session in sessions:
        focuses[session.focus] += 1
    return focuses


def recommend_next_focus(sessions: List[WorkoutSession]) -> list[str]:
    if not sessions:
        return [
            "Comienza con un entrenamiento de cuerpo completo para evaluar tu nivel actual.",
            "Registra tus levantamientos clave (sentadilla, press, peso muerto) para personalizar futuras sugerencias.",
        ]

    recent = [s for s in sessions if s.session_date >= date.today() - timedelta(days=14)]
    focus_counts = summarize_recent_sessions(recent)
    if not focus_counts:
        focus_counts = summarize_recent_sessions(sessions)

    all_groups = Counter()
    for focus, count in focus_counts.items():
        group_info = FOCUS_GROUPS.get(focus)
        group = group_info["group"] if group_info else focus
        all_groups[group] += count

    if not all_groups:
        return ["Añade notas de enfoque (Pecho, Espalda, Piernas, Core) para mejorar las recomendaciones."]

    least_trained = all_groups.most_common()[-1][0]

    recommended_focuses = [focus for focus, data in FOCUS_GROUPS.items() if data["group"] == least_trained]
    if not recommended_focuses:
        recommended_focuses = [least_trained]

    suggestions: list[str] = [
        f"Has trabajado más {all_groups.most_common(1)[0][0]}. Prioriza una sesión enfocada en {least_trained} esta semana."
    ]

    for focus in recommended_focuses:
        data = FOCUS_GROUPS.get(focus)
        if data:
            exercises = ", ".join(data["suggestions"][:3])
            suggestions.append(f"Prueba un bloque de {focus} con ejercicios como {exercises}.")
    suggestions.append("Incluye trabajo de movilidad y registra cómo te sientes después de cada sesión para ajustar la carga.")
    return suggestions


def highlight_progress(exercises: Iterable[Exercise]) -> list[str]:
    progress_messages: list[str] = []
    grouped: dict[str, list[Exercise]] = {}
    for exercise in exercises:
        grouped.setdefault(exercise.name.lower(), []).append(exercise)

    for name, entries in grouped.items():
        entries.sort(key=lambda e: e.session.session_date)
        if len(entries) < 2:
            continue
        first, last = entries[0], entries[-1]
        if last.weight and first.weight and last.weight > first.weight:
            progress_messages.append(
                f"Has incrementado {last.weight - first.weight} kg en {name.title()} desde {first.session.session_date}."
            )
    return progress_messages
