"use client";
import { useEffect, useState } from "react";

interface WeatherData {
  ville:       string;
  temp:        number;
  ressenti:    number;
  description: string;
  humidite:    number;
  vent:        number;
  icone:       string;
}

interface Props {
  ville?: string;   // depuis jarvis_config.json
}

const API_URL = "https://wttr.in/{VILLE}?format=j1";

const ICON_MAP: Record<string, string> = {
  "Sunny": "☀️", "Clear": "🌙", "Partly cloudy": "⛅",
  "Cloudy": "☁️", "Overcast": "☁️", "Mist": "🌫️",
  "Fog": "🌫️", "Light rain": "🌦️", "Moderate rain": "🌧️",
  "Heavy rain": "⛈️", "Light snow": "🌨️", "Moderate snow": "❄️",
  "Thundery outbreaks": "⛈️", "Blizzard": "🌨️",
};

export default function WeatherPanel({ ville = "Paris" }: Props) {
  const [data,    setData]    = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const url = `https://wttr.in/${encodeURIComponent(ville)}?format=j1`;
        const r = await fetch(url);
        const j = await r.json();
        const cur = j.current_condition[0];
        const desc = cur.weatherDesc[0].value;
        setData({
          ville,
          temp:        parseInt(cur.temp_C),
          ressenti:    parseInt(cur.FeelsLikeC),
          description: desc,
          humidite:    parseInt(cur.humidity),
          vent:        parseInt(cur.windspeedKmph),
          icone:       ICON_MAP[desc] ?? "🌡️",
        });
      } catch {
        // API indisponible — silence
      } finally {
        setLoading(false);
      }
    };
    load();
    // Rafraîchir toutes les 10 minutes
    const id = setInterval(load, 10 * 60 * 1000);
    return () => clearInterval(id);
  }, [ville]);

  if (!visible) return null;

  return (
    <div style={{
      position: "fixed",
      top: 72,
      left: 18,
      zIndex: 90,
      background: "rgba(10,14,26,0.7)",
      border: "1px solid rgba(76,168,232,0.12)",
      borderRadius: 8,
      padding: "10px 16px",
      backdropFilter: "blur(8px)",
      minWidth: 160,
      animation: "fadeIn 0.5s ease",
    }}>
      {/* Bouton fermer */}
      <button
        onClick={() => setVisible(false)}
        style={{
          position: "absolute", top: 4, right: 6,
          background: "none", border: "none",
          color: "rgba(76,168,232,0.3)", fontSize: 10, cursor: "pointer",
        }}
      >✕</button>

      <div style={{ fontSize: 9, letterSpacing: 3, color: "rgba(76,168,232,0.35)", textTransform: "uppercase", marginBottom: 8 }}>
        📍 {ville.toUpperCase()}
      </div>

      {loading ? (
        <div style={{ fontSize: 10, color: "rgba(76,168,232,0.3)", letterSpacing: 2 }}>chargement...</div>
      ) : data ? (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{ fontSize: 28 }}>{data.icone}</span>
            <div>
              <div style={{ fontSize: 22, color: "#00e5ff", letterSpacing: 2, lineHeight: 1 }}>
                {data.temp}°C
              </div>
              <div style={{ fontSize: 9, color: "rgba(76,168,232,0.4)", letterSpacing: 1 }}>
                ressenti {data.ressenti}°C
              </div>
            </div>
          </div>
          <div style={{ fontSize: 10, color: "rgba(76,168,232,0.55)", letterSpacing: 1, marginBottom: 6 }}>
            {data.description}
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <div style={{ fontSize: 9, color: "rgba(76,168,232,0.3)", letterSpacing: 1 }}>
              💧 {data.humidite}%
            </div>
            <div style={{ fontSize: 9, color: "rgba(76,168,232,0.3)", letterSpacing: 1 }}>
              💨 {data.vent} km/h
            </div>
          </div>
        </>
      ) : (
        <div style={{ fontSize: 10, color: "rgba(239,68,68,0.4)", letterSpacing: 1 }}>météo indisponible</div>
      )}
    </div>
  );
}
