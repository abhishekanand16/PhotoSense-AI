/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Deep Charcoal/Slate Dark Theme
        brand: {
          primary: '#8b5cf6', // Violet 500
          secondary: '#a78bfa', // Violet 400
          accent: '#2dd4bf', // Teal 400
        },
        dark: {
          bg: '#0f172a', // Slate 900
          surface: '#1e293b', // Slate 800
          border: 'rgba(255, 255, 255, 0.05)',
          text: {
            primary: '#f8fafc', // Slate 50
            secondary: '#94a3b8', // Slate 400
            tertiary: '#64748b', // Slate 500
          },
        },
        // Clean Soft Light Theme
        light: {
          bg: '#f8fafc', // Slate 50
          surface: '#ffffff',
          border: 'rgba(0, 0, 0, 0.05)',
          text: {
            primary: '#0f172a', // Slate 900
            secondary: '#475569', // Slate 600
            tertiary: '#94a3b8', // Slate 400
          },
        },
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
        'soft-lg': '0 10px 40px -4px rgba(0, 0, 0, 0.07)',
      },
    },
  },
  plugins: [],
};
