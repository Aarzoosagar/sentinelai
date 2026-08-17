/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#050505",
        card: "#111111",
        border: "#222222",
        "text-primary": "#FFFFFF",
        "text-secondary": "#9CA3AF",
        accent: {
          blue: "#3B82F6",
          green: "#10B981",
          yellow: "#F59E0B",
          red: "#EF4444",
        },
      },
      borderRadius: {
        DEFAULT: "12px",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"],
      },
      transitionDuration: {
        DEFAULT: "150ms",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(0, 0, 0, 0.4)",
      },
    },
  },
  plugins: [],
};
