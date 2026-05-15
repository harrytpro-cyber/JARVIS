"""
Morning Briefing — agrège Gmail, Calendar, tâches, météo, projets.
Génère une synthèse narrative avec Claude. Mis en cache par jour.
"""
import uuid
from datetime import date, datetime, timezone, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.memory import Task, Project, MorningBriefing
from models.integration import Integration
from core.config import settings
from core.crypto import decrypt


async def get_or_generate(db: AsyncSession, user_id: uuid.UUID, city: str = "Paris") -> str:
    today = date.today()
    existing = await db.execute(
        select(MorningBriefing).where(
            MorningBriefing.user_id == user_id,
            MorningBriefing.briefing_date == today,
        )
    )
    cached = existing.scalar_one_or_none()
    if cached:
        return cached.content

    content = await _generate(db, user_id, city)
    briefing = MorningBriefing(
        id=uuid.uuid4(),
        user_id=user_id,
        content=content,
        briefing_date=today,
    )
    db.add(briefing)
    await db.commit()
    return content


async def _generate(db: AsyncSession, user_id: uuid.UUID, city: str) -> str:
    sections: list[str] = []

    # Météo (toujours disponible, gratuit)
    weather = await _get_weather(city)
    if weather:
        sections.append(f"**Météo à {city}** : {weather}")

    # Gmail (si connecté)
    emails = await _get_gmail_summary(db, user_id)
    if emails:
        sections.append(f"**Emails non lus** ({len(emails)}) :\n" + "\n".join(f"- {e}" for e in emails[:5]))

    # Calendar (si connecté)
    events = await _get_calendar_events(db, user_id)
    if events:
        sections.append("**Agenda aujourd'hui et demain** :\n" + "\n".join(f"- {e}" for e in events))

    # Tâches prioritaires
    tasks = await _get_priority_tasks(db, user_id)
    if tasks:
        sections.append("**Tâches du jour** :\n" + "\n".join(f"- [{t.priority}] {t.title}" for t in tasks))

    # Projets actifs
    projects = await _get_active_projects(db, user_id)
    if projects:
        sections.append("**Projets actifs** : " + ", ".join(p.name for p in projects))

    raw = "\n\n".join(sections) if sections else "Aucune donnée disponible."

    # Synthèse narrative Claude
    narrative = await _synthesize(raw)
    return narrative


async def _get_weather(city: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"https://wttr.in/{city}?format=j1",
                headers={"Accept": "application/json"},
            )
            data = resp.json()
            cur = data["current_condition"][0]
            temp = cur["temp_C"]
            feels = cur["FeelsLikeC"]
            desc = cur["weatherDesc"][0]["value"]
            return f"{temp}°C (ressenti {feels}°C), {desc}"
    except Exception:
        return None


async def _get_gmail_summary(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    integ = await _get_integration(db, user_id, "google")
    if not integ or not integ.access_token:
        return []
    try:
        token = decrypt(integ.access_token)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": "is:unread", "maxResults": 10},
            )
            data = resp.json()
            messages = data.get("messages", [])
            summaries = []
            for msg in messages[:10]:
                detail = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "metadata", "metadataHeaders": ["Subject", "From"]},
                )
                headers = {h["name"]: h["value"] for h in detail.json().get("payload", {}).get("headers", [])}
                subject = headers.get("Subject", "Sans sujet")
                sender = headers.get("From", "Inconnu").split("<")[0].strip()
                summaries.append(f"{sender} — {subject}")
            return summaries
    except Exception:
        return []


async def _get_calendar_events(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    integ = await _get_integration(db, user_id, "google")
    if not integ or not integ.access_token:
        return []
    try:
        token = decrypt(integ.access_token)
        now = datetime.now(timezone.utc)
        tomorrow_end = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": now.isoformat(),
                    "timeMax": tomorrow_end.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 10,
                },
            )
            events = resp.json().get("items", [])
            result = []
            for e in events:
                start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
                dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if "T" in start else start
                label = dt.strftime("%d/%m %H:%M") if isinstance(dt, datetime) else dt
                result.append(f"{label} — {e.get('summary', 'Sans titre')}")
            return result
    except Exception:
        return []


async def _get_priority_tasks(db: AsyncSession, user_id: uuid.UUID) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id, Task.status.in_(["todo", "in_progress"]))
        .order_by(Task.priority.asc(), Task.due_date.asc().nullslast())
        .limit(3)
    )
    return list(result.scalars().all())


async def _get_active_projects(db: AsyncSession, user_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id, Project.status == "active")
        .limit(5)
    )
    return list(result.scalars().all())


async def _get_integration(db: AsyncSession, user_id: uuid.UUID, provider: str) -> Integration | None:
    result = await db.execute(
        select(Integration).where(Integration.user_id == user_id, Integration.provider == provider)
    )
    return result.scalar_one_or_none()


async def _synthesize(raw_data: str) -> str:
    if not settings.anthropic_api_key:
        return raw_data

    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Tu es JARVIS. Génère un briefing matinal concis et utile à partir de ces données.
Style : direct, informatif, légèrement motivant. Maximum 200 mots. En français.

Données :
{raw_data}"""
    msg = await client.messages.create(
        model=settings.claude_model,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
