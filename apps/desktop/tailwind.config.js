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
        // Dual-tone dark theme
        dark: {
          bg: '#0a0a0a',
          surface: '#141414',
          border: '#1f1f1f',
          text: {
            primary: '#f5f5f5',
            secondary: '#a3a3a3',
            tertiary: '#737373',
          },
        },
        // Dual-tone light theme
        light: {
          bg: '#fafafa',
          surface: '#ffffff',
          border: '#e5e5e5',
          text: {
            primary: '#171717',
            secondary: '#525252',
            tertiary: '#a3a3a3',
          },
        },
      },
    },
  },
  plugins: [],
};
