<template>
  <aside class="sidebar">
    <!-- Logo区域 -->
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-symbol">
          <span class="logo-icon">◈</span>
          <div class="logo-pulse"></div>
        </div>
        <div class="logo-text">
          <span class="logo-main">睿之兮</span>
          <span class="logo-sub">QUANT-AI</span>
        </div>
      </div>
      <div class="system-status">
        <span class="status-indicator active"></span>
        <span class="status-text">L3 ONLINE</span>
      </div>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <!-- 核心功能 -->
      <div class="nav-section">
        <div class="nav-section-header">
          <span class="nav-label">核心功能</span>
          <span class="nav-line"></span>
        </div>
        <RouterLink
          v-for="item in mainNavItems"
          :key="item.name"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-text">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </RouterLink>
      </div>

      <!-- 智能分析 -->
      <div class="nav-section">
        <div class="nav-section-header">
          <span class="nav-label">智能分析</span>
          <span class="nav-line"></span>
        </div>
        <RouterLink
          v-for="item in analysisNavItems"
          :key="item.name"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-text">{{ item.label }}</span>
        </RouterLink>
      </div>

      <!-- 系统 -->
      <div class="nav-section">
        <div class="nav-section-header">
          <span class="nav-label">系统</span>
          <span class="nav-line"></span>
        </div>
        <RouterLink
          to="/settings"
          class="nav-item"
          :class="{ active: $route.path === '/settings' }"
        >
          <span class="nav-icon">◐</span>
          <span class="nav-text">设置</span>
        </RouterLink>
      </div>
    </nav>

    <!-- 底部状态 -->
    <div class="sidebar-footer">
      <div class="connection-card">
        <div class="conn-row">
          <span class="conn-label">WS</span>
          <span class="conn-status" :class="wsStore.isConnected ? 'online' : 'offline'">
            {{ wsStore.isConnected ? 'CONNECTED' : 'OFFLINE' }}
          </span>
        </div>
        <div class="conn-row">
          <span class="conn-label">LATENCY</span>
          <span class="conn-value">{{ apiLatency }}ms</span>
        </div>
        <div class="conn-bar">
          <div class="conn-bar-fill" :style="{ width: wsStore.isConnected ? '100%' : '0%' }"></div>
        </div>
      </div>

      <div class="version-info">
        <span>v2.0.0-L3</span>
        <span class="version-dot"></span>
      </div>
    </div>

    <!-- 装饰角落 -->
    <div class="corner-accent tl"></div>
    <div class="corner-accent bl"></div>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useWebSocketStore } from '@/stores/websocket'
import { ref, onMounted } from 'vue'

const wsStore = useWebSocketStore()
const apiLatency = ref(12)

const mainNavItems = [
  { name: 'dashboard', path: '/', label: '概览面板', icon: '◉' },
  { name: 'strategies', path: '/strategies', label: '策略管理', icon: '⚡', badge: '3' },
  { name: 'backtest', path: '/backtest', label: '回测中心', icon: '◫' },
  { name: 'live', path: '/live', label: '实盘监控', icon: '◐' },
]

const analysisNavItems = [
  { name: 'intelligence', path: '/intelligence', label: '基本面分析', icon: '◈' },
  { name: 'macro', path: '/macro', label: '宏观分析', icon: '◉' },
  { name: 'industry', path: '/industry', label: '行业研究', icon: '◫' },
]

onMounted(() => {
  setInterval(() => {
    apiLatency.value = Math.floor(Math.random() * 30) + 5
  }, 5000)
})
</script>

<style scoped>
.sidebar {
  width: 260px;
  background: linear-gradient(180deg, var(--bg-deep) 0%, var(--bg-layer) 100%);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
  overflow: hidden;
}

/* 头部Logo */
.sidebar-header {
  padding: 2rem 1.5rem 1.5rem;
  border-bottom: 1px solid var(--border-subtle);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.logo-symbol {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  font-size: 1.75rem;
  color: var(--neon-cyan);
  text-shadow: 0 0 20px var(--neon-cyan);
  z-index: 1;
}

.logo-pulse {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid var(--neon-cyan);
  border-radius: 50%;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.8);
    opacity: 1;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-main {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}

.logo-sub {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--neon-cyan);
  letter-spacing: 0.2em;
  opacity: 0.7;
}

.system-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator.active {
  background: var(--neon-cyan);
  box-shadow: 0 0 10px var(--neon-cyan);
  animation: blink 2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.15em;
  color: var(--neon-cyan);
}

/* 导航菜单 */
.sidebar-nav {
  flex: 1;
  padding: 1.5rem 1rem;
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 2rem;
}

.nav-section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  padding: 0 0.5rem;
}

.nav-label {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.nav-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--border-medium), transparent);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 0.25rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 0;
  border-left: 2px solid transparent;
  transition: all 0.3s ease;
  position: relative;
}

.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0;
  background: var(--neon-cyan-dim);
  transition: width 0.3s ease;
}

.nav-item:hover {
  color: var(--text-primary);
  border-left-color: var(--neon-cyan);
}

.nav-item:hover::before {
  width: 100%;
}

.nav-item.active {
  color: var(--neon-cyan);
  border-left-color: var(--neon-cyan);
  background: var(--neon-cyan-dim);
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

.nav-icon {
  font-size: 1rem;
  width: 20px;
  text-align: center;
  z-index: 1;
}

.nav-text {
  flex: 1;
  z-index: 1;
}

.nav-badge {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  padding: 0.125rem 0.5rem;
  background: var(--neon-magenta);
  color: var(--bg-void);
  border-radius: 0;
  z-index: 1;
}

/* 底部状态 */
.sidebar-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-layer);
}

.connection-card {
  padding: 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  margin-bottom: 1rem;
}

.conn-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.conn-label {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.conn-status {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  font-weight: 600;
}

.conn-status.online {
  color: var(--neon-cyan);
  text-shadow: 0 0 10px var(--neon-cyan);
}

.conn-status.offline {
  color: var(--neon-magenta);
}

.conn-value {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--neon-amber);
}

.conn-bar {
  height: 2px;
  background: var(--bg-elevated);
  margin-top: 0.5rem;
  overflow: hidden;
}

.conn-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-amber));
  transition: width 0.5s ease;
}

.version-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
}

.version-dot {
  width: 4px;
  height: 4px;
  background: var(--neon-cyan);
  border-radius: 50%;
  animation: blink 2s ease-in-out infinite;
}

/* 装饰角落 */
.corner-accent {
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--neon-cyan);
  opacity: 0.5;
}

.corner-accent.tl {
  top: 0;
  left: 0;
  border-top: 2px solid;
  border-left: 2px solid;
}

.corner-accent.bl {
  bottom: 0;
  left: 0;
  border-bottom: 2px solid;
  border-left: 2px solid;
}

/* 响应式 */
@media (max-width: 1024px) {
  .sidebar {
    width: 70px;
  }

  .logo-text,
  .nav-text,
  .nav-label,
  .nav-line,
  .nav-badge,
  .sidebar-footer,
  .system-status {
    display: none;
  }

  .logo {
    justify-content: center;
  }

  .nav-item {
    justify-content: center;
    padding: 1rem;
  }

  .nav-icon {
    font-size: 1.25rem;
  }
}
</style>
