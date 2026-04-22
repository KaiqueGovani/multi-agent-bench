import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f6f7f9",
        ink: "#1f2933",
        muted: "#657282",
        line: "#d9dee5",
        panel: "#ffffff",
        action: "#176b87",
        success: "#2d7d46",
        warning: "#a16207",
        danger: "#b42318"
      }
    }
  },
  plugins: []
};

export default config;

