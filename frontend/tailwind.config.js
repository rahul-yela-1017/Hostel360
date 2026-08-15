/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#10233f', ink: '#1c2b3a', mint: '#12a989', cloud: '#f4f7fa', amber: '#f5a524'
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
      boxShadow: { card: '0 10px 30px rgba(20,44,72,.07)', lift: '0 18px 50px rgba(20,44,72,.14)' }
    }
  },
  plugins: []
}
