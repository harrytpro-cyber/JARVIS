# J.A.R.V.I.S

**Just A Rather Very Intelligent System** — Assistant IA personnel inspiré d'Iron Man.

Interface HUD cyan sur fond sombre, mémoire à 3 niveaux (Redis → pgvector → PostgreSQL), routage multi-LLM avec failover automatique (Claude → Gemini → Groq → Ollama), streaming SSE token-par-token.

---

## Fonctionnalités

| Catégorie | Détails |
|---|---|
| **Chat IA** | Claude Sonnet 4.6 en principal, failover Gemini / Groq / Ollama |
| **Mémoire** | Redis (session), pgvector (épisodique), PostgreSQL (tâches / projets) |
| **RAG** | Recherche sémantique cosine + recherche web (SerpAPI / Tavily) |
| **Contrôles** | Volume, screenshot, lancement d'apps, mode focus Pomodoro |
| **Tâches** | CRUD complet avec priorités, extraction automatique depuis le chat |
| **Briefing** | Résumé matinal : emails Gmail, agenda, météo, tâches du jour |
| **Musique** | Spotify (OAuth) + YouTube |
| **Auth** | JWT access + refresh, bcrypt, tokens OAuth chiffrés (Fernet) |
| **STT** | Dictée vocale fr-FR via Web Speech API |
| **Interface** | HUD Iron Man : `#020d1a` / `#00d4ff` / Courier New |

---

## Prérequis

| Outil | Version | Rôle |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | ≥ 4.x | Orchestration de tous les services |
| [Python 3.12](https://www.python.org/downloads/) | 3.12.x | Optionnel — dev local sans Docker |
| [Node.js](https://nodejs.org/) | ≥ 18.x | Optionnel — build frontend Next.js |
| Git | any | Clone du repo |

---

## Installation en 5 étapes

### 1. Cloner le projet

```bash
git clone <url-du-repo> jarvis
cd jarvis
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Ouvrez `.env` et renseignez au minimum :

```env
ANTHROPIC_API_KEY=sk-ant-...   # Obligatoire — LLM principal
OPENAI_API_KEY=sk-...          # Obligatoire — embeddings mémoire
SECRET_KEY=<32-chars-random>   # Obligatoire — sécurité JWT
JWT_SECRET_KEY=<32-chars>      # Obligatoire — tokens JWT
ENCRYPTION_KEY=<fernet-key>    # Obligatoire — chiffrement OAuth
```

Générer `ENCRYPTION_KEY` :
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Démarrer les services

```bash
make start
# ou directement :
docker compose up -d
```

### 4. Appliquer les migrations

```bash
make migrate
# ou :
docker compose exec backend alembic upgrade head
```

### 5. Ouvrir l'interface

Naviguez vers **http://localhost:3000** — créez un compte, puis commencez à parler à JARVIS.

---

## Configuration des clés API

| Service | Obligatoire | Console développeur | Usage |
|---|---|---|---|
| **Anthropic** (Claude) | Oui | [console.anthropic.com](https://console.anthropic.com/settings/keys) | LLM principal |
| **OpenAI** | Oui | [platform.openai.com](https://platform.openai.com/api-keys) | Embeddings mémoire |
| **Groq** | Recommandé | [console.groq.com](https://console.groq.com/keys) | Fallback LLM + fact extractor |
| **Gemini** | Recommandé | [aistudio.google.com](https://aistudio.google.com/app/apikey) | Fallback LLM |
| **Tavily** | Optionnel | [app.tavily.com](https://app.tavily.com/home) | Recherche web |
| **SerpAPI** | Optionnel | [serpapi.com](https://serpapi.com/manage-api-key) | Recherche web (alt.) |
| **Google OAuth** | Optionnel | [console.cloud.google.com](https://console.cloud.google.com/apis/credentials) | Gmail + Calendar |
| **Spotify** | Optionnel | [developer.spotify.com](https://developer.spotify.com/dashboard) | Contrôle musique |

---

## Commandes disponibles

```bash
make start          # Démarrer tous les services (Docker)
make stop           # Arrêter les services
make logs           # Suivre les logs en temps réel
make migrate        # Appliquer les migrations Alembic
make migrate-create # Créer une nouvelle migration
make shell-backend  # Shell Python dans le container backend
make shell-db       # Shell psql dans la base de données
```

---

## URLs accessibles

| Service | URL | Description |
|---|---|---|
| **Frontend HUD** | http://localhost:3000 | Interface principale |
| **API Backend** | http://localhost:8000 | FastAPI |
| **Docs API** | http://localhost:8000/docs | Swagger UI |
| **Health check** | http://localhost:8000/health | État DB + Redis |
| **n8n** | http://localhost:5678 | Automatisation workflows |
| **Ollama** | http://localhost:11434 | LLM local |

---

## Architecture

```
jarvis/
├── backend/
│   ├── api/v1/routers/      # 12 routers FastAPI
│   ├── core/                # Config, DB, Redis, sécurité
│   ├── models/              # SQLAlchemy ORM
│   ├── services/
│   │   ├── memory/          # Redis + pgvector + working memory + RAG
│   │   ├── llm_router.py    # Claude → Gemini → Groq → Ollama
│   │   ├── chat_service.py  # SSE streaming + mémoire
│   │   └── ...
│   └── migrations/          # Alembic (ne jamais modifier l'existant)
├── frontend/
│   ├── index.html           # Interface HUD standalone
│   └── src/                 # Next.js (App Router)
├── docker-compose.yml
├── .env                     # Variables locales (non commité)
└── .env.example             # Template des variables
```

### Ordre de fallback LLM

```
Claude Sonnet 4.6  →  Gemini 2.5 Flash  →  Groq Llama 3.3  →  Ollama (local)
```

### Pipeline RAG (10 étapes)

```
Redis (session) → pgvector (cosine) → PostgreSQL (tâches/projets) →
Recherche web → tiktoken → Résumé si >6000 tokens → LLM → Fact Extractor
```

---

## Tests

```bash
# Smoke tests (vérifie que tous les endpoints critiques répondent)
docker compose exec backend pytest tests/test_smoke.py -v

# Ou en local avec le backend qui tourne
cd backend && pytest tests/test_smoke.py -v
```

---

## Variables d'environnement complètes

Voir [.env.example](.env.example) pour la liste exhaustive avec descriptions.

---

## Licence

Usage privé — projet personnel.
