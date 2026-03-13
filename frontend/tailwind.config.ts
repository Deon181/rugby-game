import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        panel: "var(--panel)",
        panelAlt: "var(--panel-alt)",
        border: "var(--border)",
        text: "var(--text)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        accentSoft: "var(--accent-soft)",
        success: "var(--success)",
        warn: "var(--warn)",
        danger: "var(--danger)",
      },
      boxShadow: {
        panel: "0 20px 50px rgba(3, 10, 23, 0.35)",
      },
      fontFamily: {
        display: ["Rajdhani", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
