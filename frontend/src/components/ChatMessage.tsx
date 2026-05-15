"use client";
import { ChatMessage as Msg } from "@/lib/useChat";

interface Props {
  message: Msg;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-5`}>
      <div className={`max-w-[82%] ${isUser ? "order-2" : "order-1"}`}>

        {/* En-tête JARVIS */}
        {!isUser && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <div
              style={{
                width: 7, height: 7, borderRadius: "50%",
                background: "#4ca8e8",
                boxShadow: message.streaming ? "0 0 8px #4ca8e8" : undefined,
                animation: message.streaming ? "pulse-dot 1s ease-in-out infinite" : undefined,
              }}
            />
            <span style={{ color: "#4ca8e8", fontSize: 10, letterSpacing: 4, textTransform: "uppercase" }}>
              JARVIS
            </span>
            {message.model && (
              <span style={{ color: "rgba(76,168,232,0.3)", fontSize: 10, letterSpacing: 1 }}>
                · {message.model}
              </span>
            )}
          </div>
        )}

        {/* Bulle */}
        <div className={isUser ? "msg-user" : "msg-jarvis"}>
          {message.content || (
            // Placeholder pendant le chargement
            <span style={{ display: "inline-flex", alignItems: "center", gap: 3 }}>
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  style={{
                    display: "inline-block", width: 4, height: 4,
                    borderRadius: "50%", background: "#4ca8e8",
                    animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
                  }}
                />
              ))}
            </span>
          )}

          {/* Curseur clignotant en fin de stream */}
          {message.streaming && message.content && (
            <span
              style={{
                display: "inline-block", width: 2, height: "1em",
                background: "#4ca8e8", marginLeft: 3,
                verticalAlign: "text-bottom",
                animation: "blink 1s step-end infinite",
              }}
            />
          )}
        </div>

        {/* Label VOUS */}
        {isUser && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
            <span style={{ color: "rgba(76,168,232,0.3)", fontSize: 9, letterSpacing: 3, textTransform: "uppercase" }}>
              VOUS
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
