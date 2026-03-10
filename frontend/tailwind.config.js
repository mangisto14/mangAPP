/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Assistant", "sans-serif"],
      },
      colors: {
        bg: {
          deep: "#0d1520",
          base: "#111d2e",
          card: "#162033",
          border: "#1e304a",
          hover: "#1a2840",
        },
        primary: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
          light: "#3b82f6",
        },
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
        muted: "#64748b",
        text: {
          DEFAULT: "#e2e8f0",
          muted: "#94a3b8",
          dim: "#64748b",
        },
      },
    },
  },
  plugins: [],
};
