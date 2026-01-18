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
        // Blue to Teal Brand Palette
        brand: {
          primary: 'hsl(var(--brand-primary))',
          secondary: 'hsl(var(--brand-secondary))',
          accent: '#06b6d4', // Cyan 500
        },
        // High-Contrast Dark Theme
        dark: {
          bg: '#000000', // Pure Black
          surface: '#09090b', // Zinc 950
          border: 'rgba(255, 255, 255, 0.1)',
          text: {
            primary: '#ffffff', // Pure White
            secondary: '#a1a1aa', // Zinc 400
            tertiary: '#52525b', // Zinc 500
          },
        },
        // Clean Light Theme
        light: {
          bg: '#ffffff', // Pure White
          surface: '#fafafa', // Zinc 50
          border: 'rgba(0, 0, 0, 0.1)',
          text: {
            primary: '#000000', // Pure Black
            secondary: '#3f3f46', // Zinc 700
            tertiary: '#a1a1aa', // Zinc 400
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
