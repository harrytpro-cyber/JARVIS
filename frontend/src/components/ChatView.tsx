"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

import { useChat }              from "@/lib/useChat";
import { useDesktopBridge }     from "@/lib/useDesktopBridge";
import { ChatMessage }          from "./ChatMessage";
import { ChatInput }            from "./ChatInput";
import { HudOverlay }           from "./HudOverlay";
import BootScreen               from "./BootScreen";
import SubtitleHud              from "./SubtitleHud";
import TimerHud                 from "./TimerHud";
import type { TimerHandle }     from "./TimerHud";
import HelpHud                  from "./HelpHud";
import SettingsModal            from "./SettingsModal";
import WeatherPanel             from "./WeatherPanel";
import HaPanel                 from "./HaPanel";
import RecipeHud               from "./RecipeHud";
import type { JarvisConfig }    from "./SettingsModal";
import type { GlobeHandle, GlobeAction } from "./GlobeOverlay";

// Three.js : chargement côté client uniquement
const OrbCanvas    = dynamic(() => import("./OrbCanvas"),    { ssr: false });
const GlobeOverlay = dynamic(() => import("./GlobeOverlay"), { ssr: false });

interface Props {
  token:    string;
  onLogout?: () => void;
}

export function ChatView({ token, onLogout }: Props) {
  // ── Source 1 : Chat SSE (saisie clavier dans le frontend) ──────────────────
  const chat = useChat(token);

  // ── Source 2 : Bridge WebSocket (pipeline vocal desktop) ───────────────────
  const bridge = useDesktopBridge();

  // ── Fusion des états ────────────────────────────────────────────────────────
  // Si le desktop est connecté et actif → priorité bridge, sinon → chat SSE
  const orbState    = bridge.isConnected ? bridge.orbState    : chat.orbState;
  const subtitle    = bridge.isConnected ? bridge.subtitle    : chat.lastResponse;
  const showSub     = bridge.isConnected ? bridge.showSubtitle : chat.showSubtitle;

  // ── Refs & états UI ─────────────────────────────────────────────────────────
  const bottomRef    = useRef<HTMLDivElement>(null);
  const globeRef     = useRef<GlobeHandle>(null);
  const timerHandle  = useRef<TimerHandle | null>(null);

  const [booted,       setBooted]       = useState(false);
  const [showHelp,     setShowHelp]     = useState(false);
  const [showGlobe,    setShowGlobe]    = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isMuted,      setIsMuted]      = useState(false);
  const [quality,      setQuality]      = useState<"high" | "low">("high");
  const [showChat,     setShowChat]     = useState(false);
  const [showWeather,  setShowWeather]  = useState(true);

  // voiceText reçu du desktop → pré-remplir l'input (géré via ref interne ChatInput)
  const voiceTextRef = useRef("");

  // ── Scroll auto ─────────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.messages]);

  useEffect(() => {
    if (chat.messages.length > 0) setShowChat(true);
  }, [chat.messages.length]);

  // ── Réaction aux commandes timer du bridge ──────────────────────────────────
  useEffect(() => {
    const cmd = bridge.timerCmd;
    if (!cmd || !timerHandle.current) return;
    if (cmd.action === "start" && cmd.duration) {
      timerHandle.current.start(cmd.duration, cmd.label);
    } else if (cmd.action === "stop") {
      timerHandle.current.stop();
    }
  }, [bridge.timerCmd]);

  // ── Réaction aux commandes globe du bridge ──────────────────────────────────
  useEffect(() => {
    const cmd = bridge.globeCmd;
    if (!cmd) return;
    if ((cmd as GlobeAction).globe_action === "hide") {
      setShowGlobe(false);
    } else {
      setShowGlobe(true);
      setTimeout(() => globeRef.current?.dispatch(cmd as GlobeAction), 60);
    }
  }, [bridge.globeCmd]);

  // ── Réaction au texte voix reçu du desktop ──────────────────────────────────
  useEffect(() => {
    if (bridge.voiceText) {
      voiceTextRef.current = bridge.voiceText;
    }
  }, [bridge.voiceText]);

  // ── Globe : ouvrir/fermer ────────────────────────────────────────────────────
  const openGlobe = useCallback(() => {
    setShowGlobe(true);
    setTimeout(() => globeRef.current?.dispatch({ globe_action: "show_earth" }), 60);
  }, []);

  const dispatchGlobe = useCallback((action: GlobeAction) => {
    if (action.globe_action === "hide") {
      setShowGlobe(false);
    } else {
      setShowGlobe(true);
      setTimeout(() => globeRef.current?.dispatch(action), 60);
    }
  }, []);

  // Exposer jarvisGlobe globalement (utilisable depuis la console / le backend)
  useEffect(() => {
    (window as unknown as Record<string, unknown>).jarvisGlobe = dispatchGlobe;
  }, [dispatchGlobe]);

  const handleTimerRef = useCallback((h: TimerHandle) => {
    timerHandle.current = h;
  }, []);

  // ── Envoi depuis l'input clavier ─────────────────────────────────────────────
  const handleSend = useCallback((text: string) => {
    // Si le desktop est connecté, envoyer aussi au pipeline vocal
    if (bridge.isConnected) {
      bridge.sendInput(text);
    }
    // Toujours envoyer au backend SSE pour l'historique et le LLM
    chat.sendMessage(text);
  }, [bridge, chat]);

  // ── Badge connexion ──────────────────────────────────────────────────────────
  // Online si API SSE OU bridge desktop
  const anyOnline = chat.apiOnline || bridge.isConnected;

  if (!booted) {
    return <BootScreen onReady={() => setBooted(true)} />;
  }

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh", background: "#050508", overflow: "hidden" }}>

      {/* ── Orbe Three.js (plein écran, fond) ─────────────────────────────── */}
      <div style={{ position: "fixed", inset: 0, zIndex: 50, pointerEvents: "none" }}>
        <OrbCanvas state={orbState} quality={quality} />
      </div>

      {/* ── Globe 3D ──────────────────────────────────────────────────────── */}
      <GlobeOverlay
        ref={globeRef}
        isOpen={showGlobe}
        onClose={() => setShowGlobe(false)}
      />

      {/* ── HUD décoratif ─────────────────────────────────────────────────── */}
      <HudOverlay
        orbState={orbState}
        apiOnline={anyOnline}
        onHelp={() => setShowHelp(true)}
        onGlobe={() => showGlobe ? setShowGlobe(false) : openGlobe()}
        onSettings={() => {
          bridge.requestSettings();
          setShowSettings(true);
        }}
        onWeather={() => setShowWeather(v => !v)}
        isMuted={isMuted}
        onMute={() => setIsMuted(v => !v)}
        quality={quality}
        onQuality={() => setQuality(q => q === "high" ? "low" : "high")}
      />

      {/* ── Panneau météo ───────────────────────────────────────────────── */}
      {showWeather && (
        <WeatherPanel
          ville={(bridge.settingsData?.ville as string | undefined) ?? "Paris"}
        />
      )}

      {/* ── Recette HUD ─────────────────────────────────────────────────── */}
      <RecipeHud
        recipe={bridge.recipe ?? null}
        onClose={() => { /* recipe se ferme seule */ }}
      />

      {/* ── Badge Iron Man ───────────────────────────────────────────────── */}
      {bridge.ironManActive && (
        <div style={{
          position:      "fixed",
          top:           16,
          left:          "50%",
          transform:     "translateX(-50%)",
          zIndex:        90,
          fontSize:      9,
          letterSpacing: 3,
          color:         "rgba(239,68,68,0.7)",
          textTransform: "uppercase",
          animation:     "blink 1.5s ease-in-out infinite",
        }}>
          ⚡ MODE IRON MAN ACTIF
        </div>
      )}

      {/* ── Panneau Home Assistant ───────────────────────────────────────── */}
      <HaPanel
        haUrl={bridge.settingsData?.ha_url as string | undefined}
        haToken={bridge.settingsData?.ha_token as string | undefined}
        customEntities={bridge.settingsData?.ha_custom_entities as Parameters<typeof HaPanel>[0]["customEntities"]}
      />

      {/* ── Bouton déconnexion ───────────────────────────────────────────── */}
      {onLogout && (
        <button
          onClick={onLogout}
          style={{
            position:      "fixed",
            bottom:        80,
            left:          18,
            zIndex:        90,
            background:    "none",
            border:        "none",
            color:         "rgba(76,168,232,0.2)",
            fontSize:      8,
            letterSpacing: 2,
            cursor:        "pointer",
            fontFamily:    '"Courier New", Courier, monospace',
            textTransform: "uppercase",
          }}
          onMouseEnter={e => (e.currentTarget.style.color = "rgba(239,68,68,0.5)")}
          onMouseLeave={e => (e.currentTarget.style.color = "rgba(76,168,232,0.2)")}
        >
          ⏻ DÉCONNEXION
        </button>
      )}

      {/* ── Badge desktop bridge ─────────────────────────────────────────── */}
      {bridge.isConnected && (
        <div style={{
          position: "fixed", bottom: 80, right: 18, zIndex: 90,
          fontSize: 9, letterSpacing: 2, color: "rgba(0,229,255,0.4)",
          textTransform: "uppercase",
        }}>
          🎙 pipeline vocal actif
        </div>
      )}

      {/* ── Stats système (depuis le bridge) ────────────────────────────── */}
      {bridge.stats && (
        <div className="stat-hud">
          <div className="stat-line">CPU {bridge.stats.cpu}%</div>
          <div className="stat-line">RAM {bridge.stats.ram}%</div>
        </div>
      )}

      {/* ── Timer HUD ────────────────────────────────────────────────────── */}
      <TimerHud onRef={handleTimerRef} />

      {/* ── Sous-titres typewriter ───────────────────────────────────────── */}
      <SubtitleHud
        text={subtitle.slice(0, 220)}
        visible={showSub && !showChat}
      />

      {/* ── Aide commandes ───────────────────────────────────────────────── */}
      <HelpHud visible={showHelp} onClose={() => setShowHelp(false)} />

      {/* ── Modal Settings ───────────────────────────────────────────────── */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        initialCfg={bridge.settingsData as JarvisConfig | null}
        onSave={(cfg) => {
          bridge.saveSettings(cfg as unknown as Record<string, unknown>);
          setShowSettings(false);
        }}
      />

      {/* ── Zone messages (slide-up) ─────────────────────────────────────── */}
      <div
        style={{
          position: "fixed",
          bottom: 0, left: 0, right: 0,
          top: showChat ? "30%" : "100%",
          zIndex: 200,
          display: "flex",
          flexDirection: "column",
          transition: "top 0.5s cubic-bezier(0.34, 1.1, 0.64, 1)",
          background: showChat
            ? "linear-gradient(to bottom, rgba(5,5,8,0) 0%, rgba(5,5,8,0.94) 10%)"
            : "transparent",
        }}
      >
        {/* Toggle panel */}
        {chat.messages.length > 0 && (
          <div style={{ display: "flex", justifyContent: "center", padding: "8px 0 0" }}>
            <button
              className="hud-btn"
              style={{ fontSize: 9, letterSpacing: 3, padding: "5px 18px" }}
              onClick={() => setShowChat(v => !v)}
            >
              {showChat ? "▼ MASQUER" : "▲ MESSAGES"}
            </button>
          </div>
        )}

        {/* Liste messages */}
        <div
          className="scrollbar-hide"
          style={{
            flex: 1, overflowY: "auto",
            padding: "12px 20px",
            display: showChat ? "block" : "none",
          }}
        >
          <div style={{ maxWidth: 760, margin: "0 auto" }}>
            {chat.messages.map(msg => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input — toujours visible en bas */}
        <ChatInput
          onSend={handleSend}
          onAbort={chat.abort}
          isStreaming={chat.isStreaming}
          onFocus={chat.onInputFocus}
          onBlur={chat.onInputBlur}
        />
      </div>
    </div>
  );
}
