"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface Props {
  onAuth: (token: string) => void;
}

type Mode = "login" | "register";

export default function AuthScreen({ onAuth }: Props) {
  const [mode,     setMode]     = useState<Mode>("login");
  const [email,    setEmail]    = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [dots,     setDots]     = useState("...");

  // Animation des points de chargement
  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => {
      setDots(d => d.length >= 6 ? "." : d + ".");
    }, 300);
    return () => clearInterval(id);
  }, [loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "login") {
        const res = await api.auth.login({ email, password });
        localStorage.setItem("jarvis_token",         res.access_token);
        localStorage.setItem("jarvis_refresh_token", res.refresh_token ?? "");
        onAuth(res.access_token);
      } else {
        // Register puis login automatique
        await api.auth.register({ email, username, password, full_name: fullName || undefined });
        const res = await api.auth.login({ email, password });
        localStorage.setItem("jarvis_token",         res.access_token);
        localStorage.setItem("jarvis_refresh_token", res.refresh_token ?? "");
        onAuth(res.access_token);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position:        "fixed",
      inset:           0,
      background:      "#050508",
      display:         "flex",
      flexDirection:   "column",
      alignItems:      "center",
      justifyContent:  "center",
      fontFamily:      '"Courier New", Courier, monospace',
      overflow:        "hidden",
    }}>

      {/* Coins HUD */}
      {(["tl","tr","bl","br"] as const).map(pos => (
        <div key={pos} className={`hud-corner hud-corner-${pos}`} />
      ))}

      {/* Ligne de scan */}
      <div className="scan-line" />

      {/* Logo */}
      <div style={{
        fontSize:      28,
        letterSpacing: 12,
        color:         "#00e5ff",
        textShadow:    "0 0 40px rgba(0,229,255,0.6)",
        textTransform: "uppercase",
        marginBottom:  4,
      }}>
        J.A.R.V.I.S
      </div>
      <div style={{
        fontSize:      9,
        letterSpacing: 5,
        color:         "rgba(0,229,255,0.3)",
        textTransform: "uppercase",
        marginBottom:  40,
      }}>
        by Morphoz.io — Powered by Claude
      </div>

      {/* Panneau formulaire */}
      <div style={{
        background:     "rgba(10,14,26,0.7)",
        border:         "1px solid rgba(76,168,232,0.15)",
        borderRadius:   8,
        padding:        "32px 40px",
        width:          340,
        backdropFilter: "blur(12px)",
        animation:      "fadeIn 0.5s ease",
      }}>
        {/* Titre panneau */}
        <div style={{
          fontSize:      9,
          letterSpacing: 4,
          color:         "rgba(76,168,232,0.4)",
          textTransform: "uppercase",
          marginBottom:  24,
          textAlign:     "center",
        }}>
          {mode === "login" ? "⬡ AUTHENTIFICATION" : "⬡ CRÉER UN COMPTE"}
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Champ email */}
          <AuthField
            label="EMAIL"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="adresse@mail.com"
            disabled={loading}
          />

          {/* Champ username (register seulement) */}
          {mode === "register" && (
            <>
              <AuthField
                label="IDENTIFIANT"
                type="text"
                value={username}
                onChange={setUsername}
                placeholder="harry"
                disabled={loading}
              />
              <AuthField
                label="NOM COMPLET"
                type="text"
                value={fullName}
                onChange={setFullName}
                placeholder="Harry (optionnel)"
                disabled={loading}
              />
            </>
          )}

          {/* Champ mot de passe */}
          <AuthField
            label="MOT DE PASSE"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••••"
            disabled={loading}
          />

          {/* Message d'erreur */}
          {error && (
            <div style={{
              fontSize:      9,
              letterSpacing: 1,
              color:         "rgba(239,68,68,0.8)",
              textAlign:     "center",
              padding:       "6px 0",
              borderTop:     "1px solid rgba(239,68,68,0.15)",
              borderBottom:  "1px solid rgba(239,68,68,0.15)",
            }}>
              ⚠ {error.toUpperCase()}
            </div>
          )}

          {/* Bouton soumettre */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop:     8,
              padding:       "12px 0",
              background:    loading ? "rgba(76,168,232,0.05)" : "rgba(76,168,232,0.08)",
              border:        "1px solid rgba(76,168,232,0.25)",
              borderRadius:  4,
              color:         loading ? "rgba(0,229,255,0.3)" : "#00e5ff",
              fontSize:      10,
              letterSpacing: 4,
              textTransform: "uppercase",
              cursor:        loading ? "default" : "pointer",
              fontFamily:    '"Courier New", Courier, monospace',
              transition:    "all 0.2s ease",
            }}
            onMouseEnter={e => {
              if (!loading) (e.currentTarget as HTMLButtonElement).style.background = "rgba(76,168,232,0.15)";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(76,168,232,0.08)";
            }}
          >
            {loading
              ? `connexion${dots}`
              : mode === "login" ? "▶ CONNEXION" : "▶ CRÉER LE COMPTE"}
          </button>
        </form>

        {/* Toggle login/register */}
        <div style={{ marginTop: 20, textAlign: "center" }}>
          <button
            onClick={() => { setMode(m => m === "login" ? "register" : "login"); setError(""); }}
            style={{
              background:    "none",
              border:        "none",
              color:         "rgba(76,168,232,0.35)",
              fontSize:      9,
              letterSpacing: 2,
              cursor:        "pointer",
              fontFamily:    '"Courier New", Courier, monospace',
              textTransform: "uppercase",
            }}
          >
            {mode === "login" ? "Pas encore de compte ? Créer →" : "Déjà un compte ? Se connecter →"}
          </button>
        </div>
      </div>

      {/* Statut bas de page */}
      <div style={{
        position:      "fixed",
        bottom:        24,
        fontSize:      8,
        letterSpacing: 3,
        color:         "rgba(76,168,232,0.2)",
        textTransform: "uppercase",
      }}>
        MORPHOZ.IO — SECURE ACCESS
      </div>
    </div>
  );
}

// Composant champ de saisie réutilisable
function AuthField({
  label, type, value, onChange, placeholder, disabled,
}: {
  label:       string;
  type:        string;
  value:       string;
  onChange:    (v: string) => void;
  placeholder: string;
  disabled:    boolean;
}) {
  return (
    <div>
      <div style={{
        fontSize:      8,
        letterSpacing: 3,
        color:         "rgba(76,168,232,0.35)",
        textTransform: "uppercase",
        marginBottom:  5,
      }}>
        {label}
      </div>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        required
        style={{
          width:          "100%",
          background:     "rgba(10,14,26,0.8)",
          border:         "1px solid rgba(76,168,232,0.12)",
          borderRadius:   4,
          padding:        "10px 12px",
          color:          "#00e5ff",
          fontSize:       12,
          letterSpacing:  1,
          fontFamily:     '"Courier New", Courier, monospace',
          outline:        "none",
          boxSizing:      "border-box",
          transition:     "border-color 0.2s ease",
        }}
        onFocus={e  => (e.target.style.borderColor = "rgba(76,168,232,0.4)")}
        onBlur={e   => (e.target.style.borderColor = "rgba(76,168,232,0.12)")}
      />
    </div>
  );
}
