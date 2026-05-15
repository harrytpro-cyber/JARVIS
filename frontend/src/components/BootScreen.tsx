"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Module {
  id:    string;
  label: string;
  delay: number;   // ms avant activation
}

const MODULES: Module[] = [
  { id: "neural",   label: "NEURAL CORE",         delay: 400  },
  { id: "memory",   label: "MEMORY SYSTEM",        delay: 850  },
  { id: "rag",      label: "RAG PIPELINE",         delay: 1250 },
  { id: "llm",      label: "LLM ROUTER",           delay: 1650 },
  { id: "voice",    label: "VOICE ENGINE",         delay: 2050 },
  { id: "vision",   label: "VISION MODULE",        delay: 2400 },
  { id: "services", label: "EXTERNAL SERVICES",    delay: 2750 },
  { id: "api",      label: "SERVER CONNECTION",    delay: 3100 },
];

type ModuleState = "wait" | "active" | "done";

interface Props {
  onReady: () => void;
}

export default function BootScreen({ onReady }: Props) {
  const [states, setStates]     = useState<Record<string, ModuleState>>({});
  const [progress, setProgress] = useState(0);
  const [status, setStatus]     = useState("initialisation en cours...");
  const [fading, setFading]     = useState(false);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    const total = MODULES.length;

    MODULES.forEach((mod, idx) => {
      // Activation
      timers.push(setTimeout(() => {
        setStates(prev => ({ ...prev, [mod.id]: "active" }));
        setStatus(`chargement : ${mod.label.toLowerCase()}...`);
      }, mod.delay));

      // Validation du module
      timers.push(setTimeout(() => {
        setStates(prev => ({ ...prev, [mod.id]: "done" }));
        setProgress(Math.round(((idx + 1) / total) * 100));
      }, mod.delay + 340));
    });

    // Vérification API après tous les modules
    const apiDelay = MODULES[MODULES.length - 1].delay + 700;
    timers.push(setTimeout(async () => {
      setStatus("connexion au serveur...");
      try {
        const r = await fetch(`${API}/api/v1/health`, { signal: AbortSignal.timeout(4000) });
        if (r.ok) {
          setStatus("système en ligne — bienvenue, harry.");
        } else {
          setStatus("serveur hors-ligne — mode dégradé.");
        }
      } catch {
        setStatus("serveur inaccessible — mode hors-ligne.");
      }

      // Fade out après 0.8s
      timers.push(setTimeout(() => {
        setFading(true);
        timers.push(setTimeout(onReady, 800));
      }, 800));
    }, apiDelay));

    return () => timers.forEach(clearTimeout);
  }, [onReady]);

  return (
    <div
      className="boot-overlay"
      style={{ opacity: fading ? 0 : 1, pointerEvents: fading ? "none" : "all" }}
    >
      {/* Logo */}
      <div className="boot-title">J.A.R.V.I.S</div>
      <div className="boot-subtitle">by Morphoz.io — Powered by Claude</div>

      {/* Liste des modules */}
      <div style={{ minWidth: 280 }}>
        {MODULES.map(mod => {
          const s: ModuleState = states[mod.id] ?? "wait";
          return (
            <div key={mod.id} className={`boot-module ${s}`}>
              <div className="boot-module-dot" />
              <span>
                {s === "done"   ? "✓ " : s === "active" ? "▶ " : "○ "}
                {mod.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Barre de progression */}
      <div className="boot-bar">
        <div className="boot-bar-fill" style={{ width: `${progress}%` }} />
      </div>

      <div className="boot-status">{status}</div>
    </div>
  );
}
