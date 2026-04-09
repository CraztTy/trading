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
        // 赛博朋克深色主题
        'bg-void': '#020202',
        'bg-deep': '#0a0a0f',
        'bg-layer': '#12121a',
        'bg-surface': '#1a1a25',
        'bg-elevated': '#252532',

        // 霓虹强调色
        'neon-cyan': '#00f0ff',
        'neon-magenta': '#ff00aa',
        'neon-amber': '#ffb800',
        'neon-purple': '#6b2cff',

        // 信号色
        'signal-buy': '#00f0ff',
        'signal-sell': '#ff00aa',
        'signal-hold': '#ffb800',
        'signal-neutral': '#64748b',

        // 文字颜色
        'text-primary': '#ffffff',
        'text-secondary': 'rgba(255, 255, 255, 0.7)',
        'text-tertiary': 'rgba(255, 255, 255, 0.4)',
        'text-muted': 'rgba(255, 255, 255, 0.2)',

        // 边框
        'border-glow': 'rgba(0, 240, 255, 0.3)',
        'border-subtle': 'rgba(255, 255, 255, 0.06)',
        'border-medium': 'rgba(255, 255, 255, 0.12)',
      },
      fontFamily: {
        'display': ['Space Grotesk', 'Noto Sans SC', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Noto Sans SC', 'monospace'],
        'body': ['Inter', 'Noto Sans SC', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'scan': 'scan 4s linear infinite',
        'fade-in-up': 'fade-in-up 0.6s ease forwards',
        'border-flow': 'border-flow 3s linear infinite',
        'text-flicker': 'text-flicker 3s linear infinite',
        'ticker': 'ticker-scroll 20s linear infinite',
        'blink': 'blink 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1', filter: 'brightness(1)' },
          '50%': { opacity: '0.7', filter: 'brightness(1.3)' },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'fade-in-up': {
          'from': { opacity: '0', transform: 'translateY(20px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        'border-flow': {
          '0%': { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '200% 50%' },
        },
        'text-flicker': {
          '0%, 100%': { opacity: '1' },
          '41%': { opacity: '1' },
          '42%': { opacity: '0.4' },
          '43%': { opacity: '1' },
          '45%': { opacity: '0.4' },
          '46%': { opacity: '1' },
        },
        'ticker-scroll': {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        'blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0, 240, 255, 0.3)',
        'glow-magenta': '0 0 20px rgba(255, 0, 170, 0.3)',
        'glow-amber': '0 0 20px rgba(255, 184, 0, 0.3)',
        'glow-purple': '0 0 20px rgba(107, 44, 255, 0.3)',
      },
      backgroundImage: {
        'gradient-cyan': 'linear-gradient(135deg, #00f0ff, #6b2cff)',
        'gradient-amber': 'linear-gradient(135deg, #ffb800, #ff00aa)',
        'gradient-rainbow': 'linear-gradient(90deg, #00f0ff, #ff00aa, #ffb800, #00f0ff)',
      },
    },
  },
  plugins: [],
}
