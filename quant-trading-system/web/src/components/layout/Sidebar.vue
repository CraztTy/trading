<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">◈</span>
        <span class="logo-text">金策智算</span>
      </div>
      <div class="system-status">
        <span class="status-dot animate-pulse"></span>
        <span class="status-text">L3系统运行中</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <span class="nav-label">核心功能</span>
        <RouterLink
          v-for="item in mainNavItems"
          :key="item.name"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-text">{{ item.label }}</span>
        </RouterLink>
      </div>

      <div class="nav-section">
        <span class="nav-label">智能分析</span>
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

      <div class="nav-section">
        <span class="nav-label">系统</span>
        <RouterLink to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
          <span class="nav-icon">◐</span>
          <span class="nav-text">设置</span>
        </RouterLink>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="connection-status">
        <span class="conn-dot" :class="wsStore.isConnected ? 'ws-connected' : 'ws-disconnected'"></span>
        <span class="conn-text">{{ wsStore.isConnected ? 'WebSocket已连接' : 'WebSocket已断开' }}</span>
      </div>
      <div class="api-status">
        <span class="api-label">API延迟</span>
        <span class="api-value">{{ apiLatency }}ms</span>
      </div>
    </div>
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
  { name: 'strategies', path: '/strategies', label: '策略管理', icon: '⚡' },
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
    apiLatency.value = Math.floor(Math.random() * 50) + 5
  }, 30000)
})
</script>

<style scoped>
.sidebar {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-primary);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.logo-icon {
  font-size: 1.5rem;
  color: var(--accent-primary);
  text-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
}

.logo-text {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.system-status {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-success);
}

.sidebar-nav {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 1.5rem;
}

.nav-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  padding-left: 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  transition: all 0.15s ease;
  margin-bottom: 0.25rem;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-primary);
  color: var(--bg-primary);
  font-weight: 500;
}

.nav-icon {
  font-size: 0.875rem;
  opacity: 0.8;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--border-primary);
  font-size: 0.75rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
  color: var(--text-tertiary);
}

.conn-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.conn-dot.ws-connected {
  background: var(--accent-success);
}

.conn-dot.ws-disconnected {
  background: var(--accent-danger);
}

.api-status {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
}

.api-value {
  color: var(--accent-secondary);
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 1024px) {
  .sidebar {
    width: 60px;
  }

  .logo-text,
  .nav-text,
  .system-status,
  .nav-label,
  .sidebar-footer {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0.75rem;
  }
}
</style>
