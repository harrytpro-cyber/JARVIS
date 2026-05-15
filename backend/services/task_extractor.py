"""
Détecte automatiquement les tâches à créer dans une conversation.
Retourne une suggestion structurée ou None.
"""
import json
import re
from core.config import settings

_ACTION_PATTERNS = re.compile(
    r"\b(il faut|je dois|je vais|n'oublie pas|pense à|rappelle.moi|à faire|ajoute|planifie|prévois)\b",
    re.IGNORECASE,
)

_EXTRACT_PROMPT = """Analyse cet échange et détermine s'il contient une tâche concrète à faire.
Réponds UNIQUEMENT avec un JSON valide ou null.

Format si tâche détectée : {{"title": "titre court", "description": "détail optionnel", "priority": "normale|haute|critique|basse"}}
Réponds null si aucune tâche claire.

Échange :
USER: {user_msg}
JARVIS: {assistant_msg}"""


async def detect_task_suggestion(user_msg: str, assistant_msg: str) -> dict | None:
    """Retourne un dict {title, description, priority} ou None."""
    if not _ACTION_PATTERNS.search(user_msg + " " + assistant_msg):
        return None

    if not settings.groq_api_key:
        return _heuristic_extract(user_msg)

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.groq_api_key)
        resp = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": _EXTRACT_PROMPT.format(
                user_msg=user_msg[:300],
                assistant_msg=assistant_msg[:300],
            )}],
            temperature=0.1,
            max_tokens=128,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.lower() == "null":
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) and "title" in data else None
    except Exception:
        return None


def _heuristic_extract(text: str) -> dict | None:
    """Extraction basique sans LLM."""
    m = _ACTION_PATTERNS.search(text)
    if not m:
        return None
    after = text[m.end():].strip().split(".")[0][:100]
    if len(after) < 5:
        return None
    return {"title": after.capitalize(), "description": "", "priority": "normale"}
