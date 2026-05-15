"""
Niveau 3 — Mémoire de travail PostgreSQL.
Injecte tâches actives, projets et Morning Briefing dans le contexte.
Limite stricte à 800 tokens.
"""
import uuid
from datetime import date, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.memory import Task, Project, MorningBriefing

_MAX_TOKENS = 800


def _rough_token_count(text: str) -> int:
    """Estimation rapide : ~4 chars par token."""
    return len(text) // 4


async def build_working_context(db: AsyncSession, user_id: uuid.UUID) -> str:
    budget = _MAX_TOKENS
    parts: list[str] = []

    # Morning Briefing du jour
    briefing = await _get_today_briefing(db, user_id)
    if briefing:
        chunk = f"## Briefing du jour\n{briefing.content}"
        cost = _rough_token_count(chunk)
        if cost <= budget:
            parts.append(chunk)
            budget -= cost

    # Tâches prioritaires actives
    tasks = await _get_active_tasks(db, user_id)
    if tasks and budget > 100:
        lines = ["## Tâches actives"]
        for t in tasks:
            due = f" (échéance: {t.due_date.strftime('%d/%m')})" if t.due_date else ""
            lines.append(f"- [{t.priority}] {t.title}{due}")
        chunk = "\n".join(lines)
        cost = _rough_token_count(chunk)
        if cost <= budget:
            parts.append(chunk)
            budget -= cost

    # Projets actifs
    projects = await _get_active_projects(db, user_id)
    if projects and budget > 80:
        lines = ["## Projets en cours"]
        for p in projects:
            summary = f" — {p.summary[:120]}" if p.summary else ""
            lines.append(f"- {p.name}{summary}")
        chunk = "\n".join(lines)
        cost = _rough_token_count(chunk)
        if cost <= budget:
            parts.append(chunk)
            budget -= cost

    return "\n\n".join(parts)


async def _get_today_briefing(db: AsyncSession, user_id: uuid.UUID) -> MorningBriefing | None:
    today = date.today()
    result = await db.execute(
        select(MorningBriefing).where(
            MorningBriefing.user_id == user_id,
            MorningBriefing.briefing_date == today,
        )
    )
    return result.scalar_one_or_none()


async def _get_active_tasks(db: AsyncSession, user_id: uuid.UUID, limit: int = 10) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id, Task.status == "active")
        .order_by(Task.priority.asc(), Task.due_date.asc().nullslast())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _get_active_projects(db: AsyncSession, user_id: uuid.UUID, limit: int = 5) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id, Project.status == "active")
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
