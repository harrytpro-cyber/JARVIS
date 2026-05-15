"use client";
import { useEffect, useState, useCallback } from "react";

interface HaEntity {
  entity_id: string;
  state:     string;
  attributes: {
    friendly_name?: string;
    unit_of_measurement?: string;
    device_class?: string;
  };
}

interface CustomEntity {
  nom:       string;
  entity_id: string;
}

interface HaCustomEntities {
  lumieres: CustomEntity[];
  prises:   CustomEntity[];
  capteurs: CustomEntity[];
}

interface Props {
  haUrl?:          string;
  haToken?:        string;
  customEntities?: HaCustomEntities;
}

const DEVICE_ICON: Record<string, string> = {
  temperature:  "🌡️",
  humidity:     "💧",
  pressure:     "🔵",
  illuminance:  "☀️",
  motion:       "👁",
  door:         "🚪",
  window:       "🪟",
  battery:      "🔋",
  power:        "⚡",
  energy:       "⚡",
  voltage:      "⚡",
  current:      "⚡",
  gas:          "💨",
  co2:          "💨",
};

function getIcon(entity: HaEntity): string {
  const dc = entity.attributes.device_class ?? "";
  return DEVICE_ICON[dc] ?? (entity.entity_id.startsWith("light.") ? "💡"
    : entity.entity_id.startsWith("switch.") ? "🔌"
    : "📡");
}

function formatState(entity: HaEntity): string {
  const unit = entity.attributes.unit_of_measurement;
  if (entity.state === "on")  return "ON";
  if (entity.state === "off") return "OFF";
  if (entity.state === "unavailable") return "—";
  return unit ? `${entity.state} ${unit}` : entity.state;
}

export default function HaPanel({ haUrl, haToken, customEntities }: Props) {
  const [entities,  setEntities]  = useState<HaEntity[]>([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(false);
  const [visible,   setVisible]   = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  // IDs à afficher : capteurs configurés + lumières + prises
  const watchedIds: string[] = customEntities
    ? [
        ...customEntities.capteurs.map(e => e.entity_id),
        ...customEntities.lumieres.map(e => e.entity_id),
        ...customEntities.prises.map(e => e.entity_id),
      ]
    : [];

  const load = useCallback(async () => {
    if (!haUrl || !haToken || watchedIds.length === 0) return;
    setLoading(true);
    setError(false);
    try {
      const results = await Promise.all(
        watchedIds.map(id =>
          fetch(`${haUrl.replace(/\/$/, "")}/api/states/${id}`, {
            headers: { Authorization: `Bearer ${haToken}` },
          }).then(r => r.ok ? r.json() as Promise<HaEntity> : null)
        )
      );
      setEntities(results.filter((e): e is HaEntity => e !== null));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [haUrl, haToken, watchedIds.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load();
    // Rafraîchir toutes les 30 secondes
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [load]);

  if (!visible || !haUrl || !haToken || watchedIds.length === 0) return null;

  // Nom affiché : chercher dans customEntities, sinon friendly_name, sinon entity_id
  const getName = (entity: HaEntity): string => {
    const all = [
      ...(customEntities?.capteurs ?? []),
      ...(customEntities?.lumieres ?? []),
      ...(customEntities?.prises   ?? []),
    ];
    const match = all.find(e => e.entity_id === entity.entity_id);
    return match?.nom ?? entity.attributes.friendly_name ?? entity.entity_id;
  };

  return (
    <div style={{
      position:       "fixed",
      top:            72,
      right:          18,
      zIndex:         90,
      background:     "rgba(10,14,26,0.7)",
      border:         "1px solid rgba(76,168,232,0.12)",
      borderRadius:   8,
      padding:        "10px 16px",
      backdropFilter: "blur(8px)",
      minWidth:       180,
      maxWidth:       240,
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

      {/* En-tête cliquable pour réduire */}
      <div
        onClick={() => setCollapsed(v => !v)}
        style={{
          fontSize:      9,
          letterSpacing: 3,
          color:         "rgba(76,168,232,0.35)",
          textTransform: "uppercase",
          marginBottom:  collapsed ? 0 : 8,
          cursor:        "pointer",
          userSelect:    "none",
        }}
      >
        🏠 HOME ASSISTANT {collapsed ? "▶" : "▼"}
      </div>

      {!collapsed && (
        <>
          {loading && (
            <div style={{ fontSize: 10, color: "rgba(76,168,232,0.3)", letterSpacing: 2 }}>
              chargement...
            </div>
          )}

          {error && (
            <div style={{ fontSize: 10, color: "rgba(239,68,68,0.5)", letterSpacing: 1 }}>
              HA indisponible
            </div>
          )}

          {!loading && !error && entities.length === 0 && (
            <div style={{ fontSize: 10, color: "rgba(76,168,232,0.25)", letterSpacing: 1 }}>
              aucune entité
            </div>
          )}

          {entities.map(entity => {
            const stateStr = formatState(entity);
            const isOff    = entity.state === "off" || entity.state === "unavailable";
            return (
              <div
                key={entity.entity_id}
                style={{
                  display:       "flex",
                  alignItems:    "center",
                  gap:           8,
                  marginBottom:  5,
                  padding:       "3px 0",
                  borderBottom:  "1px solid rgba(76,168,232,0.06)",
                }}
              >
                <span style={{ fontSize: 13 }}>{getIcon(entity)}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize:      9,
                    color:         "rgba(76,168,232,0.45)",
                    letterSpacing: 1,
                    whiteSpace:    "nowrap",
                    overflow:      "hidden",
                    textOverflow:  "ellipsis",
                  }}>
                    {getName(entity)}
                  </div>
                  <div style={{
                    fontSize:      11,
                    color:         isOff ? "rgba(76,168,232,0.2)" : "#00e5ff",
                    letterSpacing: 1,
                    fontWeight:    isOff ? "normal" : "bold",
                  }}>
                    {stateStr}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Refresh manuel */}
          {!loading && (
            <button
              onClick={load}
              style={{
                marginTop:     4,
                background:    "none",
                border:        "none",
                color:         "rgba(76,168,232,0.25)",
                fontSize:      9,
                letterSpacing: 2,
                cursor:        "pointer",
                padding:       0,
              }}
            >
              ↻ ACTUALISER
            </button>
          )}
        </>
      )}
    </div>
  );
}
