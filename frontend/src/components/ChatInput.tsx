"use client";
import { useState, useRef, KeyboardEvent } from "react";

interface Props {
  onSend:       (content: string) => void;
  onAbort:      () => void;
  isStreaming:  boolean;
  onFocus?:     () => void;
  onBlur?:      () => void;
}

export function ChatInput({ onSend, onAbort, isStreaming, onFocus, onBlur }: Props) {
  const [value, setValue]   = useState("");
  const textareaRef         = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  };

  return (
    <div className="chat-input-zone">
      <div style={{ maxWidth: 760, margin: "0 auto" }}>

        {/* Barre de saisie style HUD */}
        <div className="kbd-input-bar">
          {/* Indicateur d'état */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, paddingBottom: 2, flexShrink: 0 }}>
            <div
              style={{
                width: 6, height: 6, borderRadius: "50%",
                background: isStreaming ? "#00e5ff" : value ? "#4ca8e8" : "rgba(76,168,232,0.2)",
                boxShadow: isStreaming ? "0 0 8px #00e5ff" : undefined,
                transition: "background 0.3s ease, box-shadow 0.3s ease",
                animation: isStreaming ? "pulse-dot 1s ease-in-out infinite" : undefined,
              }}
            />
            <div style={{ width: 1, height: 18, background: "rgba(76,168,232,0.1)" }} />
          </div>

          <textarea
            ref={textareaRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            onFocus={onFocus}
            onBlur={onBlur}
            rows={1}
            placeholder={isStreaming ? "traitement en cours..." : "Parlez à JARVIS..."}
            disabled={isStreaming}
            className="chat-textarea"
            style={{ flexGrow: 1, padding: "6px 0" }}
          />

          {/* Bouton action */}
          <button
            onClick={isStreaming ? onAbort : handleSend}
            disabled={!isStreaming && !value.trim()}
            style={{
              flexShrink: 0,
              padding: "6px 16px",
              borderRadius: 6,
              fontSize: 11,
              letterSpacing: 2,
              textTransform: "uppercase",
              fontFamily: "Courier New, monospace",
              cursor: isStreaming || value.trim() ? "pointer" : "not-allowed",
              transition: "all 0.2s ease",
              border: isStreaming
                ? "1px solid rgba(239,68,68,0.4)"
                : value.trim()
                ? "1px solid rgba(76,168,232,0.4)"
                : "1px solid rgba(76,168,232,0.1)",
              background: isStreaming
                ? "rgba(239,68,68,0.08)"
                : value.trim()
                ? "rgba(76,168,232,0.08)"
                : "transparent",
              color: isStreaming
                ? "rgba(239,68,68,0.8)"
                : value.trim()
                ? "#4ca8e8"
                : "rgba(76,168,232,0.25)",
            }}
          >
            {isStreaming ? "■ STOP" : "ENVOYER"}
          </button>
        </div>

        {/* Raccourci clavier */}
        <div style={{ textAlign: "center", marginTop: 8, fontSize: 9, letterSpacing: 2, color: "rgba(76,168,232,0.18)", textTransform: "uppercase" }}>
          Entrée pour envoyer &nbsp;·&nbsp; Shift+Entrée pour nouvelle ligne
        </div>
      </div>
    </div>
  );
}
