/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'background': '#0d0d0f',
        'surface': '#0d0d0f',
        'surface-container-low': '#131316',
        'surface-container': '#17171a',
        'surface-container-high': '#202024',
        'surface-container-highest': '#27272a',
        'surface-bright': '#27272a',
        'surface-variant': '#1c1c1f',
        'on-surface': '#e2e8f0',
        'on-surface-variant': '#94a3b8',
        'outline-variant': '#334155',
        'primary': '#10b981',
        'primary-dim': '#4edea3',
        'on-primary': '#022c22',
        'primary-container': '#064e3b',
        'secondary': '#4edea3',
        'on-secondary': '#022c22',
        'tertiary': '#f87171',
        'on-tertiary': '#450a0a',
      },
      fontFamily: {
        headline: ['Manrope', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        label: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
