"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { OrbState } from "@/components/OrbCanvas";
import type { GlobeAction } from "@/components/GlobeOverlay";

const WS_URL         = "ws://localhost:8765";
const RECONNECT_MS   = 2000;
const SPEAKING_MS    = 4000;   // durée du mode "speaking" avant retour idle

export interface TimerCmd {
  action:   "start" | "stop";
  duration?: number;
  label?:   string;
}

export interface DesktopBridgeState {
  isConnected:     boolean;
  orbState:        OrbState;
  subtitle:        string;
  showSubtitle:    boolean;
  voiceText:       string;
  timerCmd:        TimerCmd | null;
  globeCmd:        GlobeAction | null;
  stats:           { cpu: number; ram: number } | null;
  settingsData:    Record<string, unknown> | null;
  sendInput:       (text: string) => void;
  requestSettings: () => void;
  saveSettings:    (cfg: Record<string, unknown>) => void;
}

export function useDesktopBridge(): DesktopBridgeState {
  const [isConnected,  setIsConnected]  = useState(false);
  const [orbState,     setOrbState]     = useState<OrbState>("idle");
  const [subtitle,     setSubtitle]     = useState("");
  const [showSubtitle, setShowSubtitle] = useState(false);
  const [voiceText,    setVoiceText]    = useState("");
  const [timerCmd,     setTimerCmd]     = useState<TimerCmd | null>(null);
  const [globeCmd,     setGlobeCmd]     = useState<GlobeAction | null>(null);
  const [stats,        setStats]        = useState<{ cpu: number; ram: number } | null>(null);
  const [settingsData, setSettingsData] = useState<Record<string, unknown> | null>(null);

  const wsRef          = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speakTimer     = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Connexion WebSocket ──────────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (typeof window === "undefined") return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setOrbState("idle");
        // Reconnexion auto
        reconnectTimer.current = setTimeout(connect, RECONNECT_MS);
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as Record<string, unknown>;
          handleMessage(msg);
        } catch {
          // ignore malformed
        }
      };
    } catch {
      reconnectTimer.current = setTimeout(connect, RECONNECT_MS);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Traitement des messages entrants ────────────────────────────────────────
  const handleMessage = useCallback((msg: Record<string, unknown>) => {
    const type = msg.type as string;

    switch (type) {
      case "state": {
        const state = msg.state as OrbState;
        setOrbState(state);

        if (state === "speaking") {
          setShowSubtitle(true);
          // Retour idle automatique après SPEAKING_MS si pas d'autre message
          if (speakTimer.current) clearTimeout(speakTimer.current);
          speakTimer.current = setTimeout(() => {
            setOrbState("idle");
            setShowSubtitle(false);
          }, SPEAKING_MS);
        } else {
          setShowSubtitle(false);
          if (speakTimer.current) clearTimeout(speakTimer.current);
        }
        break;
      }

      case "subtitle":
        setSubtitle(msg.text as string ?? "");
        setShowSubtitle(true);
        break;

      case "voice_text":
        // Ce que l'utilisateur a dit — afficher dans le champ de saisie
        setVoiceText(msg.text as string ?? "");
        break;

      case "timer_start":
        setTimerCmd({
          action:   "start",
          duration: msg.duration as number,
          label:    msg.label as string | undefined,
        });
        break;

      case "timer_stop":
        setTimerCmd({ action: "stop" });
        break;

      case "globe":
        setGlobeCmd(msg as unknown as GlobeAction);
        break;

      case "stats":
        setStats({ cpu: msg.cpu as number, ram: msg.ram as number });
        break;

      case "settings_data":
        setSettingsData(msg.settings as Record<string, unknown>);
        break;

      case "pong":
        break;

      default:
        break;
    }
  }, []);

  // ── Init connexion ───────────────────────────────────────────────────────────
  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (speakTimer.current)     clearTimeout(speakTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // ── API sortante ─────────────────────────────────────────────────────────────
  const sendInput = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "user_input", text }));
    }
  }, []);

  const requestSettings = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "get_settings" }));
    }
  }, []);

  const saveSettings = useCallback((cfg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "update_settings", settings: cfg }));
    }
  }, []);

  return {
    isConnected,
    orbState,
    subtitle,
    showSubtitle,
    voiceText,
    timerCmd,
    globeCmd,
    stats,
    settingsData,
    sendInput,
    requestSettings,
    saveSettings,
  };
}
