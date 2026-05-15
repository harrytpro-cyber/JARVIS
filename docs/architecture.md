# JARVIS — Architecture

## Stack

| Layer      | Tech                          | Port  |
|------------|-------------------------------|-------|
| Frontend   | Next.js 14 + TailwindCSS      | 3000  |
| Backend    | Python 3.12 + FastAPI         | 8000  |
| Database   | PostgreSQL 16 + pgvector      | 5432  |
| Cache      | Redis 7                       | 6379  |
| Automation | n8n                           | 5678  |
| Local LLM  | Ollama                        | 11434 |
| LLM API    | Claude API (Anthropic)        | —     |

## Auth Flow

1. `POST /api/v1/auth/register` — création compte
2. `POST /api/v1/auth/login` — retourne access_token (30 min) + refresh_token (7 jours)
3. `POST /api/v1/auth/refresh` — renouvelle l'access_token
4. `POST /api/v1/auth/logout` — révoque le refresh_token dans Redis
5. `GET  /api/v1/auth/me` — profil utilisateur courant

## Phases

- **Phase 1a** ✅ Infra + Auth
- **Phase 1b** — Chat avec Claude, historique en base
- **Phase 2** — Mémoire vectorielle (pgvector), profil JARVIS
- **Phase 3** — Automatisations n8n, intégrations externes
