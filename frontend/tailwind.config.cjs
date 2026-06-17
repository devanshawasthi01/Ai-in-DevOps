/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // ChatGPT-style dark palette (per design spec)
        canvas:    '#0f172a', // app background
        sidebar:   '#111827', // left sidebar
        chat:      '#1e293b', // chat area
        userBubble:'#2563eb', // user message bubble
        botBubble: '#374151', // assistant message bubble
        ink:       '#f8fafc', // primary text
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      keyframes: {
        fadeInUp: {
          '0%':   { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 100%': { opacity: '0.2' },
          '50%':      { opacity: '1' },
        },
      },
      animation: {
        fadeInUp: 'fadeInUp 0.25s ease-out',
        blink:    'blink 1.2s infinite',
      },
    },
  },
  plugins: [],
}
