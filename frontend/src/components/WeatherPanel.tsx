"use client";
import { useEffect, useState, useCallback } from "react";

// ── Codes météo WMO (Open-Meteo) ────────────────────────────────────────────
const WMO: Record<number, { label: string; icon: string }> = {
  0:  { label: "Ciel dégagé",           icon: "☀️"  },
  1:  { label: "Principalement dégagé", icon: "🌤️"  },
  2:  { label: "Partiellement nuageux", icon: "⛅"   },
  3:  { label: "Couvert",               icon: "☁️"  },
  45: { label: "Brouillard",            icon: "🌫️"  },
  48: { label: "Brouillard givrant",    icon: "🌫️"  },
  51: { label: "Bruine légère",         icon: "🌦️"  },
  53: { label: "Bruine modérée",        icon: "🌦️"  },
  55: { label: "Bruine dense",          icon: "🌧️"  },
  61: { label: "Pluie légère",          icon: "🌧️"  },
  63: { label: "Pluie modérée",         icon: "🌧️"  },
  65: { label: "Pluie forte",           icon: "⛈️"  },
  71: { label: "Neige légère",          icon: "🌨️"  },
  73: { label: "Neige modérée",         icon: "❄️"  },
  75: { label: "Neige forte",           icon: "❄️"  },
  77: { label: "Grains de neige",       icon: "🌨️"  },
  80: { label: "Averses légères",       icon: "🌦️"  },
  81: { label: "Averses modérées",      icon: "🌧️"  },
  82: { label: "Averses violentes",     icon: "⛈️"  },
  85: { label: "Averses de neige",      icon: "🌨️"  },
  86: { label: "Neige abondante",       icon: "❄️"  },
  95: { label: "Orage",                 icon: "⛈️"  },
  96: { label: "Orage avec grêle",      icon: "⛈️"  },
  99: { label: "Orage violent",         icon: "⛈️"  },
};

function wmo(code: number) {
  return WMO[code] ?? { label: "Inconnu", icon: "🌡️" };
}

interface HourlyForecast {
  time:  string;
  temp:  number;
  code:  number;
}

interface WeatherData {
  temp:        number;
  ressenti:    number;
  humidite:    number;
  vent:        number;
  code:        number;
  lat:         number;
  lon:         number;
  hourly:      HourlyForecast[];
}

interface Props {
  ville?: string;
}

export default function WeatherPanel({ ville = "Paris" }: Props) {
  const [data,    setData]    = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState(true);
  const [error,   setError]   = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);

      // 1. Géocodage — nom de ville → lat/lon
      const geoRes = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(ville)}&count=1&language=fr&format=json`
      );
      const geoJson = await geoRes.json();
      const geo = geoJson.results?.[0];
      if (!geo) throw new Error("Ville introuvable");
      const { latitude: lat, longitude: lon } = geo;

      // 2. Météo courante + prévisions horaires (6 prochaines heures)
      const url = [
        "https://api.open-meteo.com/v1/forecast",
        `?latitude=${lat}&longitude=${lon}`,
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "&hourly=temperature_2m,weather_code",
        "&forecast_days=1&timezone=auto",
      ].join("");

      const meteoRes  = await fetch(url);
      const meteoJson = await meteoRes.json();
      const cur       = meteoJson.current;
      const hourly    = meteoJson.hourly;

      // On filtre les heures après maintenant (max 6)
      const now   = new Date();
      const preds: HourlyForecast[] = [];
      for (let i = 0; i < hourly.time.length && preds.length < 6; i++) {
        const t = new Date(hourly.time[i]);
        if (t > now) {
          preds.push({
            time: t.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
            temp: Math.round(hourly.temperature_2m[i]),
            code: hourly.weather_code[i],
          });
        }
      }

      setData({
        temp:     Math.round(cur.temperature_2m),
        ressenti: Math.round(cur.apparent_temperature),
        humidite: cur.relative_humidity_2m,
        vent:     Math.round(cur.wind_speed_10m),
        code:     cur.weather_code,
        lat, lon,
        hourly:   preds,
      });
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [ville]);

  useEffect(() => {
    load();
    const id = setInterval(load, 10 * 60 * 1000);
    return () => clearInterval(id);
  }, [load]);

  if (!visible) return null;

  const w = data ? wmo(data.code) : null;

  return (
    <div style={{
      position:       "fixed",
      top:            60,
      left:           18,
      zIndex:         90,
      background:     "rgba(5,8,20,0.85)",
      border:         "1px solid rgba(76,168,232,0.18)",
      borderRadius:   8,
      padding:        "10px 16px",
      backdropFilter: "blur(8px)",
      minWidth:       170,
      maxWidth:       210,
      animation:      "fadeIn 0.5s ease",
    }}>
      {/* Bouton fermer */}
      <button
        onClick={() => setVisible(false)}
        style={{
          position:   "absolute", top: 4, right: 6,
          background: "none", border: "none",
          color:      "rgba(76,168,232,0.3)", fontSize: 10, cursor: "pointer",
        }}
      >✕</button>

      {/* En-tête ville */}
      <div style={{ fontSize: 9, letterSpacing: 3, color: "rgba(76,168,232,0.35)", textTransform: "uppercase", marginBottom: 8 }}>
        📍 {ville.toUpperCase()}
      </div>

      {loading ? (
        <div style={{ fontSize: 10, color: "rgba(76,168,232,0.3)", letterSpacing: 2 }}>chargement...</div>
      ) : data && w ? (
        <>
          {/* Températures */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{ fontSize: 28 }}>{w.icon}</span>
            <div>
              <div style={{ fontSize: 22, color: "#00e5ff", letterSpacing: 2, lineHeight: 1 }}>
                {data.temp}°C
              </div>
              <div style={{ fontSize: 9, color: "rgba(76,168,232,0.4)", letterSpacing: 1 }}>
                ressenti {data.ressenti}°C
              </div>
            </div>
          </div>

          {/* Description */}
          <div style={{ fontSize: 10, color: "rgba(76,168,232,0.55)", letterSpacing: 1, marginBottom: 6 }}>
            {w.label}
          </div>

          {/* Humidité + vent */}
          <div style={{ display: "flex", gap: 12, marginBottom: 8 }}>
            <div style={{ fontSize: 9, color: "rgba(76,168,232,0.3)", letterSpacing: 1 }}>
              💧 {data.humidite}%
            </div>
            <div style={{ fontSize: 9, color: "rgba(76,168,232,0.3)", letterSpacing: 1 }}>
              💨 {data.vent} km/h
            </div>
          </div>

          {/* Prévisions horaires */}
          {data.hourly.length > 0 && (
            <>
              <div style={{ height: "1px", background: "rgba(76,168,232,0.08)", marginBottom: 6 }} />
              <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
                {data.hourly.map((h, i) => (
                  <div key={i} style={{ textAlign: "center", minWidth: 28 }}>
                    <div style={{ fontSize: 14 }}>{wmo(h.code).icon}</div>
                    <div style={{ fontSize: 9, color: "#00e5ff", letterSpacing: 1 }}>{h.temp}°</div>
                    <div style={{ fontSize: 7, color: "rgba(76,168,232,0.3)", letterSpacing: 0 }}>{h.time}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      ) : error ? (
        <div style={{ fontSize: 9, color: "rgba(76,168,232,0.3)", letterSpacing: 1 }}>
          météo indisponible
          <button
            onClick={load}
            style={{ display: "block", marginTop: 4, background: "none", border: "none",
              color: "rgba(76,168,232,0.25)", fontSize: 8, cursor: "pointer",
              fontFamily: '"Courier New", monospace', letterSpacing: 2 }}
          >↻ réessayer</button>
        </div>
      ) : null}
    </div>
  );
}
