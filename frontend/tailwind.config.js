/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          // Fond principal
          dark:    "#050508",
          panel:   "#0a0e1a",
          // Accents cyan
          blue:    "#4ca8e8",
          cyan:    "#00e5ff",
          // Borders & muted
          border:  "#1e3a5f",
          muted:   "#1a2a3a",
          // États
          success: "#22c55e",
          danger:  "#ef4444",
          warn:    "#f59e0b",
        },
      },
      fontFamily: {
        mono: ["Courier New", "Courier", "monospace"],
      },
      animation: {
        "pulse-slow":   "pulse 3s ease-in-out infinite",
        "spin-slow":    "spin 8s linear infinite",
        "fade-in":      "fadeIn 0.6s ease forwards",
        "slide-up":     "slideUp 0.4s ease forwards",
        "typewriter":   "typewriter 0.05s steps(1) forwards",
        "scan":         "scan 4s linear infinite",
      },
      keyframes: {
        fadeIn:    { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp:   { from: { opacity: "0", transform: "translateY(20px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        scan:      { from: { transform: "translateY(-100%)" }, to: { transform: "translateY(100vh)" } },
      },
    },
  },
  plugins: [],
};
