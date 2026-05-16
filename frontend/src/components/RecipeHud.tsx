"use client";
import { useState, useEffect } from "react";

export interface RecipeData {
  titre:        string;
  ingredients:  string[];
  instructions: string[];
  portions?:    number;
  temps?:       string;
}

interface Props {
  recipe:  RecipeData | null;
  onClose: () => void;
}

export default function RecipeHud({ recipe, onClose }: Props) {
  const [activeStep, setActiveStep] = useState(0);
  const [visible,    setVisible]    = useState(false);

  useEffect(() => {
    if (recipe) {
      setActiveStep(0);
      setVisible(true);
    } else {
      setVisible(false);
    }
  }, [recipe]);

  if (!visible || !recipe) return null;

  return (
    <div style={{
      position:       "fixed",
      top:            "50%",
      left:           "50%",
      transform:      "translate(-50%, -50%)",
      zIndex:         400,
      background:     "rgba(10,14,26,0.95)",
      border:         "1px solid rgba(76,168,232,0.2)",
      borderRadius:   10,
      padding:        "24px 28px",
      backdropFilter: "blur(20px)",
      width:          "min(520px, 90vw)",
      maxHeight:      "80vh",
      overflowY:      "auto",
      animation:      "fadeIn 0.4s ease",
      fontFamily:     '"Courier New", Courier, monospace',
    }}>

      {/* Bouton fermer */}
      <button
        onClick={() => { setVisible(false); onClose(); }}
        style={{
          position:   "absolute", top: 12, right: 14,
          background: "none", border: "none",
          color:      "rgba(76,168,232,0.4)", fontSize: 12, cursor: "pointer",
        }}
      >✕</button>

      {/* Titre */}
      <div style={{ fontSize: 9, letterSpacing: 4, color: "rgba(76,168,232,0.35)", textTransform: "uppercase", marginBottom: 4 }}>
        🍽️ RECETTE
      </div>
      <div style={{ fontSize: 18, color: "#00e5ff", letterSpacing: 2, marginBottom: 4 }}>
        {recipe.titre}
      </div>

      {/* Infos rapides */}
      <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
        {recipe.temps && (
          <div style={{ fontSize: 9, color: "rgba(76,168,232,0.4)", letterSpacing: 1 }}>
            ⏱ {recipe.temps}
          </div>
        )}
        {recipe.portions && (
          <div style={{ fontSize: 9, color: "rgba(76,168,232,0.4)", letterSpacing: 1 }}>
            👤 {recipe.portions} portion{recipe.portions > 1 ? "s" : ""}
          </div>
        )}
      </div>

      {/* Ingrédients */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 9, letterSpacing: 3, color: "rgba(76,168,232,0.35)", textTransform: "uppercase", marginBottom: 8 }}>
          ▸ INGRÉDIENTS
        </div>
        {recipe.ingredients.map((ing, i) => (
          <div key={i} style={{
            display:       "flex",
            alignItems:    "center",
            gap:           8,
            marginBottom:  4,
            fontSize:      11,
            color:         "rgba(76,168,232,0.7)",
            letterSpacing: 1,
          }}>
            <div style={{ width: 4, height: 4, borderRadius: "50%", background: "rgba(76,168,232,0.4)", flexShrink: 0 }} />
            {ing}
          </div>
        ))}
      </div>

      {/* Séparateur */}
      <div style={{ height: "1px", background: "rgba(76,168,232,0.08)", marginBottom: 16 }} />

      {/* Instructions étape par étape */}
      <div>
        <div style={{ fontSize: 9, letterSpacing: 3, color: "rgba(76,168,232,0.35)", textTransform: "uppercase", marginBottom: 8 }}>
          ▸ INSTRUCTIONS
        </div>
        {recipe.instructions.map((step, i) => (
          <div
            key={i}
            onClick={() => setActiveStep(i)}
            style={{
              display:       "flex",
              gap:           12,
              marginBottom:  10,
              cursor:        "pointer",
              padding:       "8px 10px",
              borderRadius:  4,
              background:    activeStep === i ? "rgba(76,168,232,0.08)" : "transparent",
              border:        `1px solid ${activeStep === i ? "rgba(76,168,232,0.2)" : "transparent"}`,
              transition:    "all 0.2s ease",
            }}
          >
            <div style={{
              minWidth:      22,
              height:        22,
              borderRadius:  "50%",
              background:    activeStep === i ? "rgba(0,229,255,0.15)" : "rgba(76,168,232,0.06)",
              border:        `1px solid ${activeStep === i ? "rgba(0,229,255,0.4)" : "rgba(76,168,232,0.15)"}`,
              display:       "flex",
              alignItems:    "center",
              justifyContent:"center",
              fontSize:      9,
              color:         activeStep === i ? "#00e5ff" : "rgba(76,168,232,0.4)",
              flexShrink:    0,
            }}>
              {i + 1}
            </div>
            <div style={{
              fontSize:      11,
              color:         activeStep === i ? "rgba(76,168,232,0.85)" : "rgba(76,168,232,0.45)",
              letterSpacing: 0.5,
              lineHeight:    1.6,
            }}>
              {step}
            </div>
          </div>
        ))}
      </div>

      {/* Navigation étapes */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
        <button
          onClick={() => setActiveStep(s => Math.max(0, s - 1))}
          disabled={activeStep === 0}
          style={{
            background:    "none",
            border:        "1px solid rgba(76,168,232,0.15)",
            borderRadius:  4,
            color:         activeStep === 0 ? "rgba(76,168,232,0.15)" : "rgba(76,168,232,0.5)",
            fontSize:      9,
            letterSpacing: 2,
            padding:       "6px 12px",
            cursor:        activeStep === 0 ? "default" : "pointer",
            fontFamily:    '"Courier New", Courier, monospace',
          }}
        >
          ← PRÉCÉDENT
        </button>

        <div style={{ fontSize: 9, color: "rgba(76,168,232,0.3)", letterSpacing: 1, alignSelf: "center" }}>
          {activeStep + 1} / {recipe.instructions.length}
        </div>

        <button
          onClick={() => setActiveStep(s => Math.min(recipe.instructions.length - 1, s + 1))}
          disabled={activeStep === recipe.instructions.length - 1}
          style={{
            background:    "none",
            border:        "1px solid rgba(76,168,232,0.15)",
            borderRadius:  4,
            color:         activeStep === recipe.instructions.length - 1 ? "rgba(76,168,232,0.15)" : "rgba(76,168,232,0.5)",
            fontSize:      9,
            letterSpacing: 2,
            padding:       "6px 12px",
            cursor:        activeStep === recipe.instructions.length - 1 ? "default" : "pointer",
            fontFamily:    '"Courier New", Courier, monospace',
          }}
        >
          SUIVANT →
        </button>
      </div>
    </div>
  );
}
