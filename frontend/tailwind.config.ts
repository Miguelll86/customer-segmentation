import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'monospace'],
      },
      colors: {
        segment: {
          business: '#0ea5e9',
          leisure: '#22c55e',
          coppia: '#ec4899',
          famiglia: '#f59e0b',
          premium: '#8b5cf6',
        },
      },
    },
  },
  plugins: [],
};
export default config;
