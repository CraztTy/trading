<template>
  <header class="top-bar">
    <div class="breadcrumb">
      <span class="current-page">{{ currentPageTitle }}</span>
      <span class="divider">/</span>
      <span class="sub-page">实时监控</span>
    </div>

    <div class="market-ticker">
      <div v-for="item in tickerItems" :key="item.symbol" class="ticker-item" :class="item.change >= 0 ? 'up' : 'down'">
        <span class="ticker-symbol">{{ item.name }}</span>
        <span class="ticker-price">{{ item.price.toLocaleString() }}</span>
        <span class="ticker-change">{{ item.change >= 0 ? '+' : '' }}{{ item.change }}%</span>
      </div>
    </div>

    <div class="top-actions">
      <button class="action-btn" @click="toggleTheme">
        <span class="btn-icon">◐</span>
      </button>
      <button class="action-btn alert" @click="toggleNotifications">
        <span class="btn-icon">◉</span>
        <span class="badge" v-if="notificationCount > 0">{{ notificationCount }}</span>
      </button>
      <div class="user-menu">
        <span class="user-avatar">QT</span>
        <span class="user-name">Quant Trader</span>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const notificationCount = ref(3)
const emit = defineEmits<{
  toggleNotifications: []
}>()

const pageTitles: Record<string, string> = {
  '/': '概览面板',
  '/strategies': '策略管理',
  '/backtest': '回测中心',
  '/live': '实盘监控',
  '/intelligence': '基本面分析',
  '/macro': '宏观分析',
  '/industry': '行业研究',
  '/settings': '设置',
}

const currentPageTitle = computed(() => pageTitles[route.path] || '概览面板')

const tickerItems = ref([
  { name: '上证指数', symbol: 'SH', price: 3085.24, change: 0.85 },
  { name: '深证成指', symbol: 'SZ', price: 9876.54, change: -0.32 },
  { name: '创业板指', symbol: 'CY', price: 1956.78, change: 1.24 },
])

function toggleTheme() {
  document.body.classList.toggle('dark')
}

function toggleNotifications() {
  emit('toggleNotifications')
}
</script>

<style scoped>
.top-bar {
  height: 60px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  position: sticky;
  top: 0;
  z-index: 50;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.current-page {
  font-weight: 600;
  color: var(--text-primary);
}

.divider {
  color: var(--text-muted);
}

.sub-page {
  color: var(--text-secondary);
}

.market-ticker {
  display: flex;
  gap: 1.5rem;
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.ticker-symbol {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.ticker-price {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
  color: var(--text-primary);
}

.ticker-change {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
}

.ticker-item.up .ticker-change {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.ticker-item.down .ticker-change {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.action-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--border-secondary);
}

.action-btn.alert .badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 16px;
  height: 16px;
  background: var(--accent-danger);
  color: white;
  font-size: 0.625rem;
  font-weight: 600;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.user-avatar {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--bg-primary);
}

.user-name {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

@media (max-width: 1024px) {
  .market-ticker {
    display: none;
  }
}
</style>
