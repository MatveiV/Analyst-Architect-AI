/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        display: ['"Syne"', 'sans-serif'],
      },
      colors: {
        ink: {
          DEFAULT: '#0f0f14',
          soft: '#1a1a24',
          muted: '#252535',
        },
        slate: {
          border: '#2e2e42',
          muted: '#9090a8',
        },
        accent: {
          DEFAULT: '#6d6aff',
          light: '#8e8cff',
          glow: 'rgba(109,106,255,0.18)',
        },
        warn: { DEFAULT: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
        danger: { DEFAULT: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
        ok: { DEFAULT: '#22c55e', bg: 'rgba(34,197,94,0.10)' },
      },
    },
  },
  plugins: [],
};
