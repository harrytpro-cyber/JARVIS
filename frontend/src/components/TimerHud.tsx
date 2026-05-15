"use client";
import { useEffect, useRef, useState } from "react";

export interface TimerHandle {
  start: (seconds: number, label?: string) => void;
  stop:  () => void;
}

interface Props {
  onRef: (handle: TimerHandle) => void;
}

export default function TimerHud({ onRef }: Props) {
  const [remaining, setRemaining] = useState<number | null>(null);
  const [label,     setLabel]     = useState("minuterie");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
    setRemaining(null);
  };

  const start = (seconds: number, lbl = "minuterie") => {
    stop();
    setLabel(lbl);
    setRemaining(seconds);
    intervalRef.current = setInterval(() => {
      setRemaining(prev => {
        if (prev === null || prev <= 1) {
          stop();
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  };

  useEffect(() => {
    onRef({ start, stop });
    return stop;
  }, [onRef]);

  if (remaining === null) return null;

  const mm  = String(Math.floor(remaining / 60)).padStart(2, "0");
  const ss  = String(remaining % 60).padStart(2, "0");
  const urgent = remaining <= 10;

  return (
    <div className="timer-hud">
      <div className={`timer-value ${urgent ? "urgent" : ""}`}>
        {mm}:{ss}
      </div>
      <div className="timer-label">{label.toUpperCase()}</div>
    </div>
  );
}
