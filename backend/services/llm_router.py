"""
LLM Router — routing intelligent par complexité.
Règle d'or : Gemini ~70% · Groq ~20% · Claude ~10%
Ordre de failover : Claude → Gemini → Groq  (Ollama skippé si OLLAMA_ENABLED=false)
"""
import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator
import httpx
from core.config import settings

log = logging.getLogger(__name__)


class TaskType(str, Enum):
    COMPLEX = "complex"   # raisonnement, mémoire, briefing → Claude
    LIGHT   = "light"     # commandes standard → Gemini  (défaut)
    FAST    = "fast"      # questions simples/rapides → Groq
    OFFLINE = "offline"   # hors connexion → Ollama


# ── Compteur de coûts session ─────────────────────────────────────────

@dataclass
class _SessionStats:
    calls:  dict[str, int]   = field(default_factory=lambda: {"claude": 0, "gemini": 0, "groq": 0, "ollama": 0})
    cost:   dict[str, float] = field(default_factory=lambda: {"claude": 0.0, "gemini": 0.0, "groq": 0.0, "ollama": 0.0})
    _lock: object            = field(default_factory=threading.Lock, repr=False)

    def record(self, provider: str, cost_usd: float):
        with self._lock:
            self.calls[provider] = self.calls.get(provider, 0) + 1
            self.cost[provider]  = self.cost.get(provider, 0.0) + cost_usd

    def log_summary(self):
        with self._lock:
            parts = []
            cost_map = {"claude": 0.005, "gemini": 0.0, "groq": 0.0, "ollama": 0.0}
            for p in ("claude", "gemini", "groq", "ollama"):
                n = self.calls.get(p, 0)
                if n:
                    c = self.cost.get(p, 0.0)
                    label = f"~{c:.3f}$" if c > 0 else "gratuit"
                    parts.append(f"{p.capitalize()} ×{n} ({label})")
            log.info(f"[COÛT] Session : {' · '.join(parts) or 'aucun appel'}")


_stats = _SessionStats()


def _start_hourly_cost_log():
    """Lance un thread qui loggue le résumé de coûts toutes les heures."""
    def _loop():
        while True:
            time.sleep(3600)
            _stats.log_summary()
    threading.Thread(target=_loop, daemon=True).start()


@dataclass
class LlmResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost_usd: float


# Coûts USD / million de tokens (prompt / completion)
_COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6":       (3.0,  15.0),
    "gemini-2.5-flash":        (0.075, 0.30),
    "llama-3.3-70b-versatile": (0.05,  0.08),
    "ollama-local":            (0.0,   0.0),
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p_rate, c_rate = _COST_TABLE.get(model, (0.0, 0.0))
    return (prompt_tokens * p_rate + completion_tokens * c_rate) / 1_000_000


def _provider_available(provider: str) -> bool:
    """Vérifie qu'un provider est configuré et non désactivé."""
    if provider == "claude":
        return bool(settings.anthropic_api_key)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    if provider == "groq":
        return bool(settings.groq_api_key)
    if provider == "ollama":
        return settings.ollama_enabled and bool(settings.ollama_base_url)
    return False


def log_provider_status() -> None:
    """Loggue le statut de chaque provider au démarrage + lance le thread de coûts."""
    statuses = {
        "claude": ("✓" if _provider_available("claude") else "✗ (clé manquante)"),
        "gemini": ("✓" if _provider_available("gemini") else "✗ (clé manquante)"),
        "groq":   ("✓" if _provider_available("groq")   else "✗ (clé manquante)"),
        "ollama": ("✓" if _provider_available("ollama") else "✗ (désactivé)" if not settings.ollama_enabled else "✗ (URL manquante)"),
    }
    log.info("=== LLM Router — statut des providers ===")
    for name, status in statuses.items():
        log.info(f"  {name:<8} {status}")
    available = [p for p in ("claude", "gemini", "groq", "ollama") if _provider_available(p)]
    if not available:
        log.error("  ⚠  AUCUN provider disponible — vérifiez le .env")
    else:
        log.info(f"  Défaut : Gemini · Fallback : {' → '.join(available)}")
    _start_hourly_cost_log()


# ── Classification intelligente ───────────────────────────────────────

def classify_task(text: str, context: dict | None = None) -> TaskType:
    """
    Règle d'or : Gemini ~70% · Groq ~20% · Claude ~10%
    Retourne le TaskType adapté à la requête.
    """
    ctx = context or {}
    t   = text.lower().strip()

    # COMPLEX → Claude (10%)
    is_complex = any([
        len(text) > 200,
        ctx.get("memory_facts_count", 0) > 3,
        any(w in t for w in [
            "analyse", "rédige", "explique en détail", "morning briefing",
            "résumé de", "stratégie", "compare", "aide-moi à réfléchir",
            "dissertation", "rapport", "bilan", "plan de", "raisonne",
        ]),
    ])
    if is_complex:
        log.info(f'[LLM] "{text[:60]}" → Claude (tâche complexe)')
        return TaskType.COMPLEX

    # FAST → Groq (20%)
    is_fast = any(w in t for w in [
        "heure", "quelle heure", "date", "aujourd'hui", "calcul", "combien",
        "convertis", "traduis", "définition", "c'est quoi", "timer",
        "rappelle-moi", "note rapide",
    ])
    if is_fast:
        log.info(f'[LLM] "{text[:60]}" → Groq (requête simple/rapide)')
        return TaskType.FAST

    # LIGHT → Gemini (70% — défaut)
    log.info(f'[LLM] "{text[:60]}" → Gemini (commande standard)')
    return TaskType.LIGHT


def _route_task(task_type: TaskType) -> list[str]:
    """Retourne la liste ordonnée de providers disponibles à essayer."""
    preferred = {
        TaskType.COMPLEX: ["claude", "gemini", "groq", "ollama"],
        TaskType.LIGHT:   ["gemini", "claude", "groq", "ollama"],
        TaskType.FAST:    ["groq",   "gemini", "claude", "ollama"],
        TaskType.OFFLINE: ["ollama", "groq", "gemini", "claude"],
    }
    order = preferred[task_type]
    available = [p for p in order if _provider_available(p)]
    if not available:
        raise RuntimeError("Aucun provider LLM disponible. Vérifiez les clés API dans le .env.")
    return available


# ── Providers ──────────────────────────────────────────────────────

async def _stream_claude(messages: list[dict], system: str) -> AsyncIterator[str]:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    async with client.messages.stream(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _stream_gemini(messages: list[dict], system: str) -> AsyncIterator[str]:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system,
    )
    history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in messages[:-1]
    ]
    chat = model.start_chat(history=history)
    response = await chat.send_message_async(messages[-1]["content"], stream=True)
    async for chunk in response:
        if chunk.text:
            yield chunk.text


async def _stream_groq(messages: list[dict], system: str) -> AsyncIterator[str]:
    from groq import AsyncGroq
    client = AsyncGroq(api_key=settings.groq_api_key)
    full_messages = [{"role": "system", "content": system}, *messages]
    stream = await client.chat.completions.create(
        model=settings.groq_model,
        messages=full_messages,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def _stream_ollama(messages: list[dict], system: str) -> AsyncIterator[str]:
    import json
    full_messages = [{"role": "system", "content": system}, *messages]
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_base_url}/api/chat",
            json={"model": settings.ollama_default_model, "messages": full_messages, "stream": True},
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content


_STREAM_FNS = {
    "claude": _stream_claude,
    "gemini": _stream_gemini,
    "groq":   _stream_groq,
    "ollama": _stream_ollama,
}

_PROVIDER_MODELS = {
    "claude": settings.claude_model,
    "gemini": settings.gemini_model,
    "groq":   settings.groq_model,
    "ollama": settings.ollama_default_model,
}


# ── Interface publique ─────────────────────────────────────────────

async def stream_response(
    messages: list[dict],
    system: str,
    task_type: TaskType | None = None,
    context: dict | None = None,
) -> AsyncIterator[tuple[str, str, str]]:
    """
    Génère des tuples (token, provider, model).
    Si task_type est None, auto-classifie d'après le dernier message utilisateur.
    Failover automatique si un provider échoue.
    """
    if task_type is None:
        user_text = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        task_type = classify_task(user_text, context)

    providers = _route_task(task_type)
    tokens_yielded: list[str] = []

    for i, provider in enumerate(providers):
        stream_fn = _STREAM_FNS[provider]
        model     = _PROVIDER_MODELS[provider]
        is_last   = i == len(providers) - 1
        try:
            async for token in stream_fn(messages, system):
                tokens_yielded.append(token)
                yield token, provider, model
            # Enregistre les stats de la session
            prompt_tok = sum(len(m["content"].split()) for m in messages)
            compl_tok  = len(tokens_yielded)
            cost       = _estimate_cost(model, prompt_tok, compl_tok)
            _stats.record(provider, cost)
            return
        except Exception as exc:
            log.warning(f"Provider '{provider}' a échoué : {exc}")
            if is_last:
                raise RuntimeError(
                    f"Tous les providers ont échoué. Dernière erreur ({provider}) : {exc}"
                ) from exc
            log.info(f"Failover vers '{providers[i+1]}'")
            continue


async def collect_response(
    messages: list[dict],
    system: str,
    task_type: TaskType = TaskType.COMPLEX,
) -> LlmResponse:
    """Version non-streamée pour usage interne (fact extractor, briefing)."""
    t0 = time.monotonic()
    tokens: list[str] = []
    provider_used = ""
    model_used = ""

    async for token, provider, model in stream_response(messages, system, task_type):
        tokens.append(token)
        provider_used = provider
        model_used = model

    content = "".join(tokens)
    latency_ms = int((time.monotonic() - t0) * 1000)
    prompt_tokens = sum(len(m["content"].split()) for m in messages)
    completion_tokens = len(content.split())

    return LlmResponse(
        content=content,
        model=model_used,
        provider=provider_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost_usd=_estimate_cost(model_used, prompt_tokens, completion_tokens),
    )
