/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // ChatGPT-inspired palette
        sidebar: {
          bg: '#171717',       // near-black sidebar
          hover: '#2a2a2a',    // hover state
          active: '#212121',   // active item
          border: '#2d2d2d',   // sidebar border
          text: '#ececec',     // primary text
          muted: '#8e8ea0',    // muted text
        },
        canvas: {
          bg: '#212121',       // main content background
          surface: '#2f2f2f',  // card / input surface
          border: '#3d3d3d',   // border
          hover: '#3a3a3a',    // hover surface
        },
        accent: {
          DEFAULT: '#10a37f',  // ChatGPT green
          hover: '#0d8f6f',
          muted: '#1a3d35',
          text: '#10a37f',
        },
        // Keep semantic colors
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
          800: '#166534',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#f59e0b',
          600: '#d97706',
          800: '#92400e',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          600: '#dc2626',
          800: '#991b1b',
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      boxShadow: {
        'soft': '0 1px 3px rgba(0,0,0,0.4)',
        'medium': '0 4px 12px rgba(0,0,0,0.5)',
        'strong': '0 8px 24px rgba(0,0,0,0.6)',
        'glow': '0 0 20px rgba(16,163,127,0.25)',
      },
    },
  },
  plugins: [],
}
