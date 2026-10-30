module.exports = {
  content: ['./frontend/index.html', './frontend/js/app.js', './frontend/js/pages.js'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['Playfair Display', 'Georgia', 'serif'],
        script: ['Caveat', 'cursive'],
        ui: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
      },
      colors: {
        irisDark: '#0A090F', irisGold: '#D4AF37', irisGoldDark: '#B8962E',
        irisOrange: '#E58929', irisPurple: '#7C3AED', irisPurpleLight: '#A78BFA',
        irisSecondary: '#A1A1AA', irisMuted: '#6B6B7B',
      },
    },
  },
};
