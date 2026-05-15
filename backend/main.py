from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from core.config import settings
from core.redis import close_redis
from api.v1.routers import (
    auth, health, chat, memory,
    tasks, projects, system, briefing,
    control, integrations, music, search,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.llm_router import log_provider_status
    log_provider_status()
    yield
    await close_redis()


app = FastAPI(
    title="JARVIS API",
    description="Just A Rather Very Intelligent System — personal AI assistant",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.allowed_origins,
    allow_credentials=False if settings.debug else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.jarvis.local"],
)

# ─── Routers ─────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(briefing.router, prefix="/api/v1")
app.include_router(control.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(music.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
