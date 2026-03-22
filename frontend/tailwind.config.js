/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", "[data-theme='dark']"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Assistant", "sans-serif"],
      },
      colors: {
        bg: {
          deep:   "rgb(var(--bg-deep-rgb)   / <alpha-value>)",
          base:   "rgb(var(--bg-base-rgb)   / <alpha-value>)",
          card:   "rgb(var(--bg-card-rgb)   / <alpha-value>)",
          border: "rgb(var(--bg-border-rgb) / <alpha-value>)",
          hover:  "rgb(var(--bg-hover-rgb)  / <alpha-value>)",
        },
        primary: {
          DEFAULT: "rgb(var(--primary-rgb)       / <alpha-value>)",
          hover:   "rgb(var(--primary-hover-rgb) / <alpha-value>)",
          light:   "rgb(var(--primary-light-rgb) / <alpha-value>)",
        },
        secondary: "rgb(var(--secondary-rgb) / <alpha-value>)",
        "on-primary": "#ffffff",
        success: "#22c55e",
        warning: "#f59e0b",
        danger:  "#ef4444",
        muted:   "#64748b",
        text: {
          DEFAULT: "rgb(var(--text-rgb)       / <alpha-value>)",
          muted:   "rgb(var(--text-muted-rgb) / <alpha-value>)",
          dim:     "rgb(var(--text-dim-rgb)   / <alpha-value>)",
        },
      },
      keyframes: {
        shake: {
          "0%,100%": { transform: "translateX(0)" },
          "20%":     { transform: "translateX(-8px)" },
          "40%":     { transform: "translateX(8px)" },
          "60%":     { transform: "translateX(-6px)" },
          "80%":     { transform: "translateX(6px)" },
        },
      },
      animation: {
        shake: "shake 0.6s ease-in-out",
      },
    },
  },
  plugins: [],
};
