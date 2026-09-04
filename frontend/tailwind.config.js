/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#e0e9fe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#0f172a',
        },
        fintech: {
          bg: '#0B0F17',
          card: '#131A29',
          border: '#1E293B',
          accent: '#00D2FF',
          green: '#10B981',
          amber: '#F59E0B',
          red: '#EF4444',
        }
      }
    },
  },
  plugins: [],
}
