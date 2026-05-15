"use client";
import { useEffect, useState } from "react";

const ALL_COMMANDS = [
  "Quelle heure est-il à Tokyo ?",
  "Mets de la musique",
  "Lance Chrome",
  "Règle le volume à 60%",
  "Note ça : rappel réunion",
  "Combien font 144 divisé par 12 ?",
  "Convertis 50 km en miles",
  "Minuterie de 5 minutes",
  "Traduis merci en japonais",
  "Montre-moi la météo",
  "Ouvre YouTube",
  "Éteins l'ordinateur dans 10 minutes",
  "Quelle est la capitale du Japon ?",
  "Lis mes emails",
  "Crée un document Google",
  "Ajoute du lait à ma liste de courses",
];

interface Props {
  visible: boolean;
  onClose: () => void;
}

export default function HelpHud({ visible, onClose }: Props) {
  const [cmds, setCmds] = useState<{ text: string; side: "left" | "right"; top: number }[]>([]);

  useEffect(() => {
    if (!visible) return;
    const shuffled = [...ALL_COMMANDS].sort(() => Math.random() - 0.5).slice(0, 14);
    const result = shuffled.map((text, i) => ({
      text,
      side: (i % 2 === 0 ? "left" : "right") as "left" | "right",
      top:  8 + (i / 2) * 6.5,
    }));
    setCmds(result);
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 350,
        background: "rgba(5, 5, 8, 0.7)",
        backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
      onClick={onClose}
    >
      {/* Titre central */}
      <div style={{ textAlign: "center", pointerEvents: "none" }}>
        <div style={{ fontSize: 11, letterSpacing: 5, color: "rgba(0,229,255,0.4)", textTransform: "uppercase", marginBottom: 6 }}>
          Commandes disponibles
        </div>
        <div style={{ fontSize: 9, letterSpacing: 3, color: "rgba(76,168,232,0.25)", textTransform: "uppercase" }}>
          Cliquer pour fermer
        </div>
      </div>

      {/* Commandes flottantes */}
      {cmds.map((cmd, i) => (
        <div
          key={i}
          className={`help-cmd ${cmd.side}`}
          style={{
            top:   `${cmd.top}%`,
            left:  cmd.side === "left"  ? "4%"  : undefined,
            right: cmd.side === "right" ? "4%"  : undefined,
            animationDelay: `${i * 0.04}s`,
          }}
        >
          {cmd.side === "left" && "— "}
          {cmd.text}
          {cmd.side === "right" && " —"}
        </div>
      ))}
    </div>
  );
}
