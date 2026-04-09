/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 深色主题
        'bg-primary': '#0a0b0d',
        'bg-secondary': '#111318',
        'bg-tertiary': '#1a1d24',
        'bg-elevated': '#22262e',
        'bg-hover': '#2a2f38',
        // 强调色
        'accent-primary': '#f59e0b',
        'accent-secondary': '#06b6d4',
        'accent-success': '#10b981',
        'accent-danger': '#ef4444',
        'accent-warning': '#f59e0b',
        // 文字颜色
        'text-primary': '#f8fafc',
        'text-secondary': '#94a3b8',
        'text-tertiary': '#64748b',
        'text-muted': '#475569',
        // 边框
        'border-primary': '#1e293b',
        'border-secondary': '#334155',
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
        'serif': ['Noto Serif SC', 'Songti SC', 'serif'],
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
