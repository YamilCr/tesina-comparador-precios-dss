import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      boxShadow: {
        float: '0 24px 60px -28px rgb(15 23 42 / 0.42)',
        glass: '0 20px 45px -24px rgb(30 64 175 / 0.34)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      keyframes: {
        drift: {
          '0%, 100%': { transform: 'translate3d(0, 0, 0)' },
          '50%': { transform: 'translate3d(0, -14px, 0)' },
        },
      },
      animation: {
        drift: 'drift 8s ease-in-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
