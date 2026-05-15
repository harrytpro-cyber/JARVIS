"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import type { OrbState } from "@/components/OrbCanvas";

export interface ChatMessage {
  id:        string;
  role:      "user" | "assistant";
  content:   string;
  model?:    string;
  provider?: string;
  streaming?: boolean;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Durée pendant laquelle l'orbe reste en mode "speaking" après fin de stream
const SPEAKING_DURATION_MS = 4000;

export function useChat(token: string) {
  const [messages,        setMessages]        = useState<ChatMessage[]>([]);
  const [isStreaming,     setIsStreaming]      = useState(false);
  const [conversationId,  setConversationId]  = useState<string | null>(null);
  const [orbState,        setOrbState]        = useState<OrbState>("idle");
  const [lastResponse,    setLastResponse]    = useState("");   // dernière réponse complète pour SubtitleHud
  const [showSubtitle,    setShowSubtitle]    = useState(false);
  const [apiOnline,       setApiOnline]       = useState(false);

  const abortRef       = useRef<AbortController | null>(null);
  const speakTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Vérification santé API ─────────────────────────────────────────────────
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API}/api/v1/health`, { signal: AbortSignal.timeout(3000) });
        setApiOnline(r.ok);
      } catch {
        setApiOnline(false);
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  // ── Transition idle après "speaking" ──────────────────────────────────────
  const scheduleIdle = useCallback(() => {
    if (speakTimerRef.current) clearTimeout(speakTimerRef.current);
    speakTimerRef.current = setTimeout(() => {
      setOrbState("idle");
      setShowSubtitle(false);
    }, SPEAKING_DURATION_MS);
  }, []);

  // ── Envoi d'un message ─────────────────────────────────────────────────────
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return;

    if (speakTimerRef.current) clearTimeout(speakTimerRef.current);

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content };
    setMessages(prev => [...prev, userMsg]);
    setOrbState("thinking");
    setIsStreaming(true);
    setShowSubtitle(false);

    const assistantId = crypto.randomUUID();
    setMessages(prev => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", streaming: true },
    ]);

    abortRef.current = new AbortController();

    try {
      const params = new URLSearchParams({ content });
      if (conversationId) params.set("conversation_id", conversationId);

      const res = await fetch(`${API}/api/v1/chat/stream?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal:  abortRef.current.signal,
      });

      if (!res.body) throw new Error("Pas de stream reçu");

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";
      let fullText  = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (!json) continue;

          const data: {
            token?:           string;
            done?:            boolean;
            error?:           string;
            model?:           string;
            provider?:        string;
            conversation_id?: string;
          } = JSON.parse(json);

          if (data.error) {
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: `[Erreur] ${data.error}`, streaming: false }
                  : m,
              ),
            );
            break;
          }

          if (data.conversation_id && !conversationId) {
            setConversationId(data.conversation_id);
          }

          if (data.done) {
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId
                  ? { ...m, streaming: false, model: data.model, provider: data.provider }
                  : m,
              ),
            );
            // Passer en mode "speaking" + afficher sous-titre
            setLastResponse(fullText);
            setOrbState("speaking");
            setShowSubtitle(true);
            scheduleIdle();
          } else if (data.token) {
            fullText += data.token;
            setMessages(prev =>
              prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: m.content + data.token, model: data.model, provider: data.provider }
                  : m,
              ),
            );
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantId
              ? { ...m, content: "[Connexion interrompue]", streaming: false }
              : m,
          ),
        );
        setOrbState("idle");
      }
    } finally {
      setIsStreaming(false);
    }
  }, [token, conversationId, isStreaming, scheduleIdle]);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setOrbState("idle");
    setShowSubtitle(false);
  }, []);

  // ── Écoute : quand l'utilisateur commence à taper ─────────────────────────
  const onInputFocus = useCallback(() => {
    if (orbState === "idle") setOrbState("listening");
  }, [orbState]);

  const onInputBlur = useCallback(() => {
    if (orbState === "listening") setOrbState("idle");
  }, [orbState]);

  return {
    messages,
    sendMessage,
    isStreaming,
    abort,
    conversationId,
    orbState,
    lastResponse,
    showSubtitle,
    apiOnline,
    onInputFocus,
    onInputBlur,
  };
}
