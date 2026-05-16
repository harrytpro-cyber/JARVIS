"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

// Chargement côté client uniquement (hooks localStorage)
const AuthScreen = dynamic(() => import("@/components/AuthScreen"), { ssr: false });
const ChatViewDyn = dynamic(
  () => import("@/components/ChatView").then(m => ({ default: m.ChatView })),
  { ssr: false }
);

export default function Home() {
  const [token,   setToken]   = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  // Au montage : récupère le token stocké en localStorage
  useEffect(() => {
    const stored = localStorage.getItem("jarvis_token");
    setToken(stored ?? null);
    setChecked(true);
  }, []);

  const handleAuth = (newToken: string) => {
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem("jarvis_token");
    localStorage.removeItem("jarvis_refresh_token");
    setToken(null);
  };

  // Attendre la vérification localStorage avant de rendre quoi que ce soit
  if (!checked) return null;

  if (!token) {
    return <AuthScreen onAuth={handleAuth} />;
  }

  return <ChatViewDyn token={token} onLogout={handleLogout} />;
}
