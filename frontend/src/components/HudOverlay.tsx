"use client";
import { useEffect, useState } from "react";
import type { OrbState } from "./OrbCanvas";

const STATUS_LABELS: Record<OrbState, string> = {
  idle:      "en veille",
  listening: "à l'écoute...",
  thinking:  "traitement en cours...",
  speaking:  "réponse",
};

interface Props {
  orbState:    OrbState;
  apiOnline:   boolean;
  onHelp:      () => void;
  onGlobe:     () => void;
  onSettings:  () => void;
  onWeather:   () => void;
  isMuted:     boolean;
  onMute:      () => void;
  quality:     "high" | "low";
  onQuality:   () => void;
}

export function HudOverlay({
  orbState, apiOnline, onHelp, onGlobe, onSettings, onWeather, isMuted, onMute, quality, onQuality,
}: Props) {
  const [time, setTime] = useState({ hms: "", date: "" });

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime({
        hms:  now.toLocaleTimeString("fr-FR", { hour12: false }),
        date: now.toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "short" }).toUpperCase(),
      });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      {/* Ligne de scan lente */}
      <div className="scan-line" />

      {/* Coins HUD */}
      <div className="hud-corner hud-corner-tl" />
      <div className="hud-corner hud-corner-tr" />
      <div className="hud-corner hud-corner-bl" />
      <div className="hud-corner hud-corner-br" />

      {/* ── Boutons haut-gauche ─────────────────────────────────────────── */}
      <div style={{ position: "fixed", top: 16, left: 16, display: "flex", gap: 10, zIndex: 500 }}>
        <button
          className={`hud-btn ${isMuted ? "danger" : ""}`}
          onClick={onMute}
        >
          {isMuted ? "🔇 MUET" : "🎙 SON"}
        </button>

        <button
          className={`hud-btn ${quality === "low" ? "off" : ""}`}
          onClick={onQuality}
          title="Qualité graphique"
        >
          GPU {quality === "high" ? "HI" : "LO"}
        </button>

        <button className="hud-btn" onClick={onHelp}>
          ? AIDE
        </button>

        <button className="hud-btn" onClick={onGlobe}>
          🌐 GLOBE
        </button>

        <button className="hud-btn" onClick={onSettings}>
          ⚙ CONFIG
        </button>

        <button className="hud-btn" onClick={onWeather}>
          🌤 MÉTÉO
        </button>
      </div>

      {/* ── Badge connexion haut-droite ─────────────────────────────────── */}
      <div style={{ position: "fixed", top: 16, right: 16, zIndex: 500 }}>
        <div className={`connection-badge ${apiOnline ? "connected" : "disconnected"}`}>
          <div className="connection-dot" />
          <span className="connection-label">
            {apiOnline ? "morphoz.io — online" : "hors-ligne"}
          </span>
        </div>
      </div>

      {/* ── Heure temps réel bas-droite ─────────────────────────────────── */}
      <div className="clock-hud">
        <div className="clock-time">{time.hms}</div>
        <div className="clock-date">{time.date}</div>
      </div>

      {/* ── Heure sous l'orbe (centre) ──────────────────────────────────── */}
      <div className="orb-time">
        <div className="orb-time-value">{time.hms}</div>
        <div className="orb-date-value">{time.date}</div>
      </div>

      {/* ── Statut orbe bas-centre ───────────────────────────────────────── */}
      <div className={`orb-status ${orbState}`}>
        {STATUS_LABELS[orbState]}
      </div>

      {/* ── Label assistant très discret ────────────────────────────────── */}
      <div className="assistant-label">by morphoz.io</div>
    </>
  );
}
