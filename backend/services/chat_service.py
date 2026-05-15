import uuid
import time
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
from models.conversation import Conversation, Message, LlmLog
from models.user import User
from services.llm_router import stream_response, TaskType, _estimate_cost
from services.memory import redis_memory
from services.memory.rag_pipeline import (
    build_context_and_messages,
    post_response_tasks,
    detect_memory_command,
)
from services.memory.vector_memory import (
    save_memory, list_top_memories, delete_memory, delete_all_memories, search_similar
)
from typing import AsyncIterator


def _classify_task(content: str) -> TaskType:
    cl = content.lower()
    if any(k in cl for k in ["heure", "date", "calcul", "combien", "quelle heure", "timer"]):
        return TaskType.FAST
    if any(k in cl for k in ["météo", "weather", "température", "traduction", "traduis", "résume"]):
        return TaskType.LIGHT
    return TaskType.COMPLEX


class ChatService:
    def __init__(self, db: AsyncSession, session_factory: async_sessionmaker | None = None):
        self.db = db
        self.session_factory = session_factory

    async def get_or_create_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID | None) -> Conversation:
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv
        conv = Conversation(user_id=user_id)
        self.db.add(conv)
        await self.db.flush()
        return conv

    async def save_message(self, conversation_id: uuid.UUID, role: str, content: str, model: str | None = None) -> Message:
        msg = Message(conversation_id=conversation_id, role=role, content=content, model_used=model)
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def log_llm_call(self, user_id, conversation_id, model, provider, prompt_tokens, completion_tokens, latency_ms, success=True, error=None):
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)
        log = LlmLog(
            id=uuid.uuid4(), user_id=user_id, conversation_id=conversation_id,
            model=model, provider=provider, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, latency_ms=latency_ms,
            cost_usd=cost, success=success, error=error,
        )
        self.db.add(log)
        await self.db.flush()

    # ── Commandes mémoire ──────────────────────────────────────────
    async def handle_memory_command(self, user: User, content: str) -> str | None:
        cmd = detect_memory_command(content)
        if cmd is None:
            return None

        if cmd == "memorize":
            fact = content.split("que", 1)[-1].strip().lstrip(",. ")
            await save_memory(self.db, user.id, fact, memory_type="fact", importance=0.8)
            await self.db.commit()
            return f"Mémorisé : « {fact} »."

        if cmd == "list":
            memories = await list_top_memories(self.db, user.id)
            if not memories:
                return "Je n'ai encore rien mémorisé à votre sujet."
            lines = [f"Voici ce que je sais sur vous ({len(memories)} faits) :"]
            for i, m in enumerate(memories, 1):
                lines.append(f"{i}. [{m.memory_type}] {m.content} (importance : {m.importance:.1f})")
            return "\n".join(lines)

        if cmd == "forget":
            target = content[len("oublie "):].strip()
            similar = await search_similar(self.db, user.id, target, top_k=1)
            if similar:
                await delete_memory(self.db, user.id, similar[0].id)
                await self.db.commit()
                return f"J'ai supprimé ce souvenir : « {similar[0].content} »."
            return "Je n'ai rien trouvé correspondant à votre demande."

        if cmd == "delete_all":
            return "__CONFIRM_DELETE_ALL__"

        return None

    async def confirm_delete_all(self, user_id: uuid.UUID) -> str:
        count = await delete_all_memories(self.db, user_id)
        await redis_memory.clear_session(user_id)
        await self.db.commit()
        return f"Mémoire effacée. {count} souvenir(s) supprimé(s)."

    # ── Stream principal avec RAG ──────────────────────────────────
    async def stream_chat(
        self,
        user: User,
        content: str,
        conversation_id: uuid.UUID | None = None,
    ) -> AsyncIterator[str]:
        # Commandes mémoire → réponse directe sans LLM
        mem_reply = await self.handle_memory_command(user, content)
        if mem_reply == "__CONFIRM_DELETE_ALL__":
            yield f"data: {json.dumps({'token': 'Confirmation requise : tapez « CONFIRMER » pour effacer toute votre mémoire.', 'done': False})}\n\n"
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
            return
        if mem_reply is not None:
            for chunk in mem_reply.split(" "):
                yield f"data: {json.dumps({'token': chunk + ' ', 'done': False})}\n\n"
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
            return

        conv = await self.get_or_create_conversation(user.id, conversation_id)
        task_type = _classify_task(content)

        # RAG : construit système + messages enrichis
        system, llm_messages = await build_context_and_messages(
            db=self.db, user=user, new_message=content, task_type=task_type
        )

        # Pousse le message user dans Redis
        await redis_memory.push_message(user.id, "user", content)

        full_response: list[str] = []
        provider_used = ""
        model_used = ""
        t0 = time.monotonic()
        error_occurred = None

        try:
            async for token, provider, model in stream_response(llm_messages, system, task_type):
                full_response.append(token)
                provider_used = provider
                model_used = model
                yield f"data: {json.dumps({'token': token, 'done': False, 'model': model, 'provider': provider, 'conversation_id': str(conv.id)})}\n\n"
        except Exception as exc:
            error_occurred = str(exc)
            yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"

        latency_ms = int((time.monotonic() - t0) * 1000)
        final_content = "".join(full_response)

        # Sauvegarde en base + Redis
        if final_content:
            await self.save_message(conv.id, "user", content)
            await self.save_message(conv.id, "assistant", final_content, model_used)
            await redis_memory.push_message(user.id, "assistant", final_content)

        prompt_tokens = sum(len(m["content"].split()) for m in llm_messages)
        completion_tokens = len(final_content.split())
        await self.log_llm_call(
            user.id, conv.id, model_used or "unknown", provider_used or "unknown",
            prompt_tokens, completion_tokens, latency_ms,
            success=error_occurred is None, error=error_occurred,
        )
        await self.db.commit()

        # Fact Extractor en arrière-plan
        if final_content and self.session_factory:
            full_conv = llm_messages + [{"role": "assistant", "content": final_content}]
            await post_response_tasks(user.id, full_conv, self.session_factory)

        # Détection de tâche suggérée
        if final_content and not error_occurred:
            from services.task_extractor import detect_task_suggestion
            suggestion = await detect_task_suggestion(content, final_content)
            if suggestion:
                yield f"data: {json.dumps({'type': 'task_suggestion', 'task': suggestion, 'done': False})}\n\n"

        if not error_occurred:
            yield f"data: {json.dumps({'token': '', 'done': True, 'model': model_used, 'provider': provider_used, 'conversation_id': str(conv.id), 'latency_ms': latency_ms})}\n\n"
