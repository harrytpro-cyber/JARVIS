"use client";
import { useEffect, useState } from "react";

export interface JarvisConfig {
  user_name:   string;
  ville:       string;
  mic_device_index: number | null;
  musique_lien: string;
  custom_apps:  { name: string; path: string }[];
  ha_url:       string;
  ha_token:     string;
  ha_custom_entities: {
    lumieres: { nom: string; entity_id: string }[];
    prises:   { nom: string; entity_id: string }[];
    capteurs: { nom: string; entity_id: string }[];
  };
}

const DEFAULT_CONFIG: JarvisConfig = {
  user_name:   "Harry",
  ville:       "Paris",
  mic_device_index: null,
  musique_lien: "",
  custom_apps:  [],
  ha_url:       "",
  ha_token:     "",
  ha_custom_entities: { lumieres: [], prises: [], capteurs: [] },
};

interface Props {
  isOpen:     boolean;
  onClose:    () => void;
  onSave:     (cfg: JarvisConfig) => void;
  initialCfg: JarvisConfig | null;
}

// ── Composant champ HA entité ────────────────────────────────────────────────
function EntityRow({
  item,
  onChange,
  onRemove,
}: {
  item:     { nom: string; entity_id: string };
  onChange: (field: "nom" | "entity_id", val: string) => void;
  onRemove: () => void;
}) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
      <input
        className="settings-input"
        placeholder="Nom vocal (ex: salon)"
        value={item.nom}
        onChange={e => onChange("nom", e.target.value)}
        style={{ flex: 1 }}
      />
      <input
        className="settings-input"
        placeholder="entity_id (ex: light.salon)"
        value={item.entity_id}
        onChange={e => onChange("entity_id", e.target.value)}
        style={{ flex: 2 }}
      />
      <button className="settings-btn-danger" onClick={onRemove}>✕</button>
    </div>
  );
}

// ── Composant app personnalisée ───────────────────────────────────────────────
function AppRow({
  item,
  onChange,
  onRemove,
}: {
  item:     { name: string; path: string };
  onChange: (field: "name" | "path", val: string) => void;
  onRemove: () => void;
}) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
      <input
        className="settings-input"
        placeholder="Nom vocal (ex: Photoshop)"
        value={item.name}
        onChange={e => onChange("name", e.target.value)}
        style={{ flex: 1 }}
      />
      <input
        className="settings-input"
        placeholder="Chemin exe (ex: C:\Program Files\...)"
        value={item.path}
        onChange={e => onChange("path", e.target.value)}
        style={{ flex: 2 }}
      />
      <button className="settings-btn-danger" onClick={onRemove}>✕</button>
    </div>
  );
}

// ── Modal principal ───────────────────────────────────────────────────────────
export default function SettingsModal({ isOpen, onClose, onSave, initialCfg }: Props) {
  const [cfg, setCfg] = useState<JarvisConfig>(initialCfg ?? DEFAULT_CONFIG);
  const [tab, setTab] = useState<"general" | "apps" | "ha">("general");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (initialCfg) setCfg(initialCfg);
  }, [initialCfg]);

  if (!isOpen) return null;

  const set = <K extends keyof JarvisConfig>(key: K, val: JarvisConfig[K]) =>
    setCfg(prev => ({ ...prev, [key]: val }));

  const handleSave = () => {
    onSave(cfg);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const addApp = () =>
    set("custom_apps", [...cfg.custom_apps, { name: "", path: "" }]);

  const updateApp = (i: number, field: "name" | "path", val: string) =>
    set("custom_apps", cfg.custom_apps.map((a, idx) => idx === i ? { ...a, [field]: val } : a));

  const removeApp = (i: number) =>
    set("custom_apps", cfg.custom_apps.filter((_, idx) => idx !== i));

  const addEntity = (cat: "lumieres" | "prises" | "capteurs") =>
    set("ha_custom_entities", {
      ...cfg.ha_custom_entities,
      [cat]: [...cfg.ha_custom_entities[cat], { nom: "", entity_id: "" }],
    });

  const updateEntity = (cat: "lumieres" | "prises" | "capteurs", i: number, field: "nom" | "entity_id", val: string) =>
    set("ha_custom_entities", {
      ...cfg.ha_custom_entities,
      [cat]: cfg.ha_custom_entities[cat].map((e, idx) => idx === i ? { ...e, [field]: val } : e),
    });

  const removeEntity = (cat: "lumieres" | "prises" | "capteurs", i: number) =>
    set("ha_custom_entities", {
      ...cfg.ha_custom_entities,
      [cat]: cfg.ha_custom_entities[cat].filter((_, idx) => idx !== i),
    });

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 600,
      background: "rgba(5,5,8,0.85)", backdropFilter: "blur(8px)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        width: "min(680px, 95vw)",
        background: "rgba(10,14,26,0.98)",
        border: "1px solid rgba(76,168,232,0.2)",
        borderRadius: 12,
        boxShadow: "0 0 60px rgba(0,229,255,0.08)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        maxHeight: "85vh",
      }}>

        {/* ── En-tête ────────────────────────────────────────────────── */}
        <div style={{
          padding: "18px 24px",
          borderBottom: "1px solid rgba(76,168,232,0.1)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div>
            <div style={{ fontSize: 13, letterSpacing: 4, color: "#00e5ff", textTransform: "uppercase" }}>
              Configuration JARVIS
            </div>
            <div style={{ fontSize: 9, letterSpacing: 3, color: "rgba(76,168,232,0.35)", marginTop: 3, textTransform: "uppercase" }}>
              Morphoz.io — jarvis_config.json
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "rgba(76,168,232,0.4)", fontSize: 18, cursor: "pointer" }}
          >✕</button>
        </div>

        {/* ── Onglets ────────────────────────────────────────────────── */}
        <div style={{ display: "flex", borderBottom: "1px solid rgba(76,168,232,0.08)", padding: "0 24px" }}>
          {(["general", "apps", "ha"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "12px 18px 10px",
                background: "none",
                border: "none",
                borderBottom: tab === t ? "2px solid #00e5ff" : "2px solid transparent",
                color: tab === t ? "#00e5ff" : "rgba(76,168,232,0.35)",
                fontSize: 10,
                letterSpacing: 3,
                textTransform: "uppercase",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {t === "general" ? "Général" : t === "apps" ? "Applications" : "Home Assistant"}
            </button>
          ))}
        </div>

        {/* ── Contenu ────────────────────────────────────────────────── */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px" }} className="scrollbar-hide">

          {/* ── Onglet Général ───────────────────────────────────────── */}
          {tab === "general" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <SettingsField label="Prénom" hint="Utilisé par JARVIS pour vous appeler">
                <input
                  className="settings-input"
                  value={cfg.user_name}
                  onChange={e => set("user_name", e.target.value)}
                  placeholder="Harry"
                />
              </SettingsField>

              <SettingsField label="Ville" hint="Pour la météo et l'heure locale">
                <input
                  className="settings-input"
                  value={cfg.ville}
                  onChange={e => set("ville", e.target.value)}
                  placeholder="Paris"
                />
              </SettingsField>

              <SettingsField label="Index microphone" hint="Laisser vide pour le micro par défaut (0, 1, 2...)">
                <input
                  className="settings-input"
                  type="number"
                  min={0}
                  value={cfg.mic_device_index ?? ""}
                  onChange={e => set("mic_device_index", e.target.value === "" ? null : parseInt(e.target.value))}
                  placeholder="Défaut (vide)"
                />
              </SettingsField>

              <SettingsField label="Lien musique" hint="URL YouTube, Spotify ou autre — lancé par 'mets ma musique'">
                <input
                  className="settings-input"
                  value={cfg.musique_lien}
                  onChange={e => set("musique_lien", e.target.value)}
                  placeholder="https://open.spotify.com/playlist/..."
                />
              </SettingsField>
            </div>
          )}

          {/* ── Onglet Applications ───────────────────────────────────── */}
          {tab === "apps" && (
            <div>
              <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(76,168,232,0.4)", marginBottom: 16, textTransform: "uppercase" }}>
                Applications personnalisées — "lance [nom]"
              </div>
              {cfg.custom_apps.map((app, i) => (
                <AppRow
                  key={i}
                  item={app}
                  onChange={(f, v) => updateApp(i, f, v)}
                  onRemove={() => removeApp(i)}
                />
              ))}
              <button className="settings-btn-add" onClick={addApp}>+ Ajouter une application</button>
            </div>
          )}

          {/* ── Onglet Home Assistant ─────────────────────────────────── */}
          {tab === "ha" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <SettingsField label="URL Home Assistant" hint="Ex: http://192.168.1.100:8123">
                <input
                  className="settings-input"
                  value={cfg.ha_url}
                  onChange={e => set("ha_url", e.target.value)}
                  placeholder="http://homeassistant.local:8123"
                />
              </SettingsField>

              <SettingsField label="Token HA" hint="Paramètres → Sécurité → Tokens d'accès longue durée">
                <input
                  className="settings-input"
                  type="password"
                  value={cfg.ha_token}
                  onChange={e => set("ha_token", e.target.value)}
                  placeholder="eyJ0eXAiOiJKV1QiLCJhbGci..."
                />
              </SettingsField>

              {/* Lumières */}
              <div>
                <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(76,168,232,0.4)", marginBottom: 10, textTransform: "uppercase" }}>
                  💡 Lumières
                </div>
                {cfg.ha_custom_entities.lumieres.map((e, i) => (
                  <EntityRow key={i} item={e}
                    onChange={(f, v) => updateEntity("lumieres", i, f, v)}
                    onRemove={() => removeEntity("lumieres", i)}
                  />
                ))}
                <button className="settings-btn-add" onClick={() => addEntity("lumieres")}>+ Ajouter lumière</button>
              </div>

              {/* Prises */}
              <div>
                <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(76,168,232,0.4)", marginBottom: 10, textTransform: "uppercase" }}>
                  🔌 Prises connectées
                </div>
                {cfg.ha_custom_entities.prises.map((e, i) => (
                  <EntityRow key={i} item={e}
                    onChange={(f, v) => updateEntity("prises", i, f, v)}
                    onRemove={() => removeEntity("prises", i)}
                  />
                ))}
                <button className="settings-btn-add" onClick={() => addEntity("prises")}>+ Ajouter prise</button>
              </div>

              {/* Capteurs */}
              <div>
                <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(76,168,232,0.4)", marginBottom: 10, textTransform: "uppercase" }}>
                  📡 Capteurs
                </div>
                {cfg.ha_custom_entities.capteurs.map((e, i) => (
                  <EntityRow key={i} item={e}
                    onChange={(f, v) => updateEntity("capteurs", i, f, v)}
                    onRemove={() => removeEntity("capteurs", i)}
                  />
                ))}
                <button className="settings-btn-add" onClick={() => addEntity("capteurs")}>+ Ajouter capteur</button>
              </div>
            </div>
          )}
        </div>

        {/* ── Pied de page ───────────────────────────────────────────── */}
        <div style={{
          padding: "14px 24px",
          borderTop: "1px solid rgba(76,168,232,0.08)",
          display: "flex", justifyContent: "flex-end", gap: 12,
        }}>
          <button className="hud-btn off" onClick={onClose}>Annuler</button>
          <button
            className="hud-btn"
            onClick={handleSave}
            style={saved ? { background: "rgba(34,197,94,0.15)", borderColor: "rgba(34,197,94,0.4)", color: "#22c55e" } : {}}
          >
            {saved ? "✓ Sauvegardé" : "Sauvegarder"}
          </button>
        </div>
      </div>

      {/* ── Styles inline Settings ─────────────────────────────────────── */}
      <style>{`
        .settings-input {
          width: 100%;
          background: rgba(5,5,8,0.6);
          border: 1px solid rgba(76,168,232,0.15);
          border-radius: 6px;
          padding: 8px 12px;
          color: #4ca8e8;
          font-family: "Courier New", monospace;
          font-size: 12px;
          letter-spacing: 1px;
          outline: none;
          transition: border-color 0.2s;
        }
        .settings-input:focus {
          border-color: rgba(76,168,232,0.4);
          box-shadow: 0 0 12px rgba(76,168,232,0.06);
        }
        .settings-input::placeholder { color: rgba(76,168,232,0.2); }
        .settings-btn-danger {
          background: rgba(239,68,68,0.08);
          border: 1px solid rgba(239,68,68,0.2);
          border-radius: 4px;
          color: rgba(239,68,68,0.7);
          padding: 6px 10px;
          cursor: pointer;
          font-size: 11px;
          transition: all 0.2s;
        }
        .settings-btn-danger:hover { background: rgba(239,68,68,0.16); }
        .settings-btn-add {
          background: rgba(76,168,232,0.06);
          border: 1px dashed rgba(76,168,232,0.2);
          border-radius: 6px;
          color: rgba(76,168,232,0.5);
          padding: 8px 16px;
          cursor: pointer;
          font-family: "Courier New", monospace;
          font-size: 11px;
          letter-spacing: 1px;
          width: 100%;
          margin-top: 4px;
          transition: all 0.2s;
        }
        .settings-btn-add:hover {
          background: rgba(76,168,232,0.12);
          color: rgba(76,168,232,0.8);
          border-color: rgba(76,168,232,0.35);
        }
      `}</style>
    </div>
  );
}

// ── Helper label + hint ───────────────────────────────────────────────────────
function SettingsField({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 10, letterSpacing: 2, color: "rgba(76,168,232,0.6)", textTransform: "uppercase", marginBottom: 6 }}>
        {label}
      </div>
      {children}
      <div style={{ fontSize: 9, letterSpacing: 1, color: "rgba(76,168,232,0.25)", marginTop: 4 }}>
        {hint}
      </div>
    </div>
  );
}
