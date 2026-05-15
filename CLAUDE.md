# JARVIS — Instructions Claude Code

## Langue
Réponds **toujours en français** dans toutes les réponses, explications, commentaires de code et messages.

---

## Architecture figée — ne jamais modifier sans confirmation explicite
- **LLM Router** : `llm_router.py` — ordre de fallback Claude→Gemini→Groq→Ollama immuable
- **RAG Pipeline** : `rag_pipeline.py` — séquence en 10 étapes validée, ne pas réorganiser
- **Mémoire 3 niveaux** : `redis_memory.py` / `vector_memory.py` / `working_memory.py` — ne pas fusionner
- **Auth JWT** : middleware existant — ne jamais contourner pour les routes protégées
- **Design HUD** : fond `#020d1a`, texte `#00d4ff`, police Courier New — ne jamais modifier

---

## Conventions obligatoires
- Tout nouveau service dans `backend/services/`
- Tout nouveau endpoint dans `backend/api/v1/routers/`
- Toute nouvelle table = migration Alembic dédiée
- Chaque appel LLM loggé dans `llm_logs`
- Isolation `user_id` sur toutes les tables sans exception
- Backend : Python, async partout, SQLAlchemy 2.x, Pydantic v2
- Frontend : TypeScript strict, App Router Next.js 14, Tailwind — pas de `any`
- Pas de commentaires évidents — seulement si le "pourquoi" est non-obvie

---

## Stack figée
- Backend : Python 3.12 + FastAPI + SQLAlchemy + Alembic
- Frontend : Next.js 14 + TailwindCSS + TypeScript
- Base : PostgreSQL 16 + pgvector + Redis 7
- LLM principal : `claude-sonnet-4-6` via Anthropic SDK
- Déploiement : Docker Compose

---

## Fichiers sensibles — ne jamais modifier
- `docker-compose.yml` (sauf ajout explicitement demandé)
- `backend/migrations/` (toujours créer une nouvelle migration, jamais modifier l'existante)
- `.env.example` (ajouter uniquement, ne jamais supprimer une variable)

---

## Services existants — ne pas réécrire
- `llm_router.py` : routage multi-LLM avec failover
- `jarvis_personality.py` : system prompt, 3 modes
- `chat_service.py` : stream SSE + logs llm_logs
- `memory/redis_memory.py` : Niveau 1, TTL 7200s, 30 msgs max
- `memory/vector_memory.py` : Niveau 2, pgvector, cosine search, dédup 0.92
- `memory/working_memory.py` : Niveau 3, tâches + projets + briefing, max 800 tokens
- `memory/fact_extractor.py` : extraction async Groq, max 5 faits/échange
- `memory/rag_pipeline.py` : orchestrateur complet Redis→pgvector→PG→tiktoken→LLM

---

## Patterns obligatoires
- Chaque nouveau service injecte ses dépendances via FastAPI `Depends()`
- Toujours vérifier `user_id` depuis le JWT, jamais depuis le body de la requête
- Les opérations mémoire sont toujours asynchrones (`async/await`)
- Les erreurs LLM sont catchées et loggées avant de remonter au client

---

## Design HUD validé — immuable
- Fond : `#020d1a`
- Texte principal : `#00d4ff` (cyan)
- Police : Courier New, monospace
- Animations : canvas 2D, cercles concentriques, scanner rotatif
- Composants existants : `ChatView.tsx`, `ChatMessage.tsx`, `ChatInput.tsx`, `HudOverlay.tsx`

---

## Conventions frontend
- Tout appel API via le hook `useChat.ts` existant
- Le streaming SSE est géré dans `useChat.ts` — ne pas dupliquer
- Les nouveaux composants suivent le même style cyan sur fond sombre
- TypeScript strict — pas de `any`
