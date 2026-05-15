"""
Service d'embedding.
Ordre de priorité : OpenAI text-embedding-3-small → Groq (via hash déterministe) → local hash.
Pas de crash si aucune clé externe n'est configurée.
"""
import hashlib
import logging
import struct
import httpx
from core.config import settings

log = logging.getLogger(__name__)

VECTOR_DIM = 1536  # text-embedding-3-small ; dimension cible pour pgvector


def _openai_available() -> bool:
    key = settings.openai_api_key
    return bool(key) and "REMPLACE" not in key and len(key) > 20


async def embed(text: str) -> list[float]:
    """Retourne un vecteur normalisé de dimension 1536."""
    if _openai_available():
        try:
            return await _embed_openai(text)
        except Exception as exc:
            log.warning(f"OpenAI embedding échoué, fallback local : {exc}")

    if settings.ollama_enabled and settings.ollama_base_url:
        try:
            return await _embed_ollama(text)
        except Exception as exc:
            log.warning(f"Ollama embedding échoué, fallback local : {exc}")

    return _embed_local(text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    if _openai_available():
        try:
            return await _embed_openai_batch(texts)
        except Exception as exc:
            log.warning(f"OpenAI batch embedding échoué, fallback local : {exc}")
    return [await embed(t) for t in texts]


async def _embed_openai(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": "text-embedding-3-small", "input": text},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


async def _embed_openai_batch(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": "text-embedding-3-small", "input": texts},
        )
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [d["embedding"] for d in data]


async def _embed_ollama(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
        )
        resp.raise_for_status()
        vec = resp.json()["embedding"]
    if len(vec) < VECTOR_DIM:
        vec = vec + [0.0] * (VECTOR_DIM - len(vec))
    return vec[:VECTOR_DIM]


def _embed_local(text: str) -> list[float]:
    """
    Embedding déterministe basé sur SHA-256.
    Pas de recherche sémantique réelle — à remplacer par OpenAI quand disponible.
    Garantit le démarrage sans aucune clé externe.
    """
    seed = text.encode("utf-8")
    floats: list[float] = []
    block = 0
    while len(floats) < VECTOR_DIM:
        digest = hashlib.sha256(seed + block.to_bytes(4, "big")).digest()
        for j in range(0, len(digest) - 3, 4):
            val = struct.unpack_from(">i", digest, j)[0]
            floats.append(val / 2_147_483_648.0)
        block += 1

    vec = floats[:VECTOR_DIM]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]
