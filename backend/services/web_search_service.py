"""
Recherche web — SerpAPI (prioritaire) ou Tavily (fallback).
Retourne une chaîne prête à injecter dans le system prompt.
"""
import httpx
from core.config import settings

_SEARCH_TRIGGERS = {
    "cherche", "trouve", "actualité", "aujourd'hui",
    "prix de", "météo", "c'est quoi", "qu'est-ce que",
    "news", "récent", "dernier", "dernière",
}


def _needs_search(text: str) -> bool:
    tl = text.lower()
    return any(t in tl for t in _SEARCH_TRIGGERS)


async def maybe_search_web(query: str) -> str:
    """Retourne '' si pas de recherche nécessaire ou aucune clé disponible."""
    if not _needs_search(query):
        return ""
    results = await search(query)
    if not results:
        return ""
    lines = ["## Résultats de recherche web"]
    for r in results[:3]:
        lines.append(f"- **{r['title']}** — {r['snippet']} ({r['url']})")
    return "\n".join(lines)


async def search(query: str) -> list[dict]:
    if settings.serpapi_key:
        return await _serpapi(query)
    if settings.tavily_key:
        return await _tavily(query)
    return []


async def _serpapi(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": settings.serpapi_key, "num": 3, "hl": "fr"},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"title": r.get("title", ""), "snippet": r.get("snippet", ""), "url": r.get("link", "")}
            for r in data.get("organic_results", [])[:3]
        ]


async def _tavily(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": settings.tavily_key, "query": query, "max_results": 3},
        )
        resp.raise_for_status()
        return [
            {"title": r.get("title", ""), "snippet": r.get("content", "")[:200], "url": r.get("url", "")}
            for r in resp.json().get("results", [])[:3]
        ]
