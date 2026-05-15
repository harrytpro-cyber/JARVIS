"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  text:    string;   // texte complet à afficher
  visible: boolean;
}

export default function SubtitleHud({ text, visible }: Props) {
  const [displayed, setDisplayed] = useState("");
  const [showCursor, setShowCursor] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const idxRef   = useRef(0);

  useEffect(() => {
    if (!visible || !text) {
      setDisplayed("");
      setShowCursor(false);
      idxRef.current = 0;
      return;
    }

    // Vitesse adaptée à la longueur (comme TechEnClair)
    const speed = text.length > 80 ? 14 : 22;
    idxRef.current = 0;
    setDisplayed("");
    setShowCursor(true);

    function tick() {
      if (idxRef.current >= text.length) {
        // Curseur disparaît 2.5s après la fin
        timerRef.current = setTimeout(() => setShowCursor(false), 2500);
        return;
      }
      setDisplayed(text.slice(0, idxRef.current + 1));
      idxRef.current++;
      timerRef.current = setTimeout(tick, speed);
    }
    tick();

    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [text, visible]);

  if (!visible && !displayed) return null;

  return (
    <div
      className="subtitle-hud"
      style={{ opacity: visible ? 1 : 0, transition: "opacity 0.5s ease" }}
    >
      <div className="subtitle-text">
        {displayed}
        {showCursor && <span className="subtitle-cursor" />}
      </div>
    </div>
  );
}
