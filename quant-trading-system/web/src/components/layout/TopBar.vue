<template>
  <header class="top-bar">
    <!-- 左侧：面包屑 -->
    <div class="breadcrumb">
      <div class="breadcrumb-icon">{{ pageIcon }}</div>
      <div class="breadcrumb-content">
        <span class="page-id">{{ pageId }}</span>
        <span class="page-title">{{ currentPageTitle }}</span>
      </div>
    </div>

    <!-- 中间：市场行情滚动 -->
    <div class="market-ticker">
      <div class="ticker-track">
        <div
          v-for="item in tickerItems"
          :key="item.symbol"
          class="ticker-item"
          :class="item.change >= 0 ? 'bull' : 'bear'"
        >
          <span class="ticker-symbol">{{ item.symbol }}</span>
          <span class="ticker-price data-value">{{ item.price.toFixed(2) }}</span>
          <span class="ticker-change">
            <span class="change-icon">{{ item.change >= 0 ? '▲' : '▼' }}</span>
            {{ Math.abs(item.change).toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 右侧：操作区 -->
    <div class="top-actions">
      <!-- 时间显示 -->
      <div class="time-display">
        <span class="time-value">{{ currentTime }}</span>
        <span class="time-label">UTC+8</span>
      </div>

      <!-- 分隔线 -->
      <div class="action-divider"></div>

      <!-- 通知按钮 -->
      <button class="cyber-icon-btn alert" @click="toggleNotifications">
        <span class="btn-glow"></span>
        <span class="btn-icon">◉</span>
        <span v-if="notificationCount > 0" class="btn-badge">{{ notificationCount }}</span>
      </button>

      <!-- 用户菜单 -->
      <div class="user-menu">
        <div class="user-avatar">
          <span>QT</span>
          <div class="avatar-ring"></div>
        </div>
        <div class="user-info">
          <span class="user-name">Quant Trader</span>
          <span class="user-role">L3 Analyst</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const notificationCount = ref(3)
const currentTime = ref('')
let timeInterval: number | null = null

const emit = defineEmits<{
  toggleNotifications: []
}>()

const pageConfig: Record<string, { title: string; icon: string; id: string }> = {
  '/': { title: '概览面板', icon: '◉', id: 'DASH-01' },
  '/strategies': { title: '策略管理', icon: '⚡', id: 'STRAT-02' },
  '/backtest': { title: '回测中心', icon: '◫', id: 'TEST-03' },
  '/live': { title: '实盘监控', icon: '◐', id: 'LIVE-04' },
  '/intelligence': { title: '基本面分析', icon: '◈', id: 'INTEL-05' },
  '/macro': { title: '宏观分析', icon: '◉', id: 'MACRO-06' },
  '/industry': { title: '行业研究', icon: '◫', id: 'IND-07' },
  '/settings': { title: '系统设置', icon: '◐', id: 'CONF-08' },
}

const currentPage = computed(() => pageConfig[route.path] || pageConfig['/'])
const currentPageTitle = computed(() => currentPage.value.title)
const pageIcon = computed(() => currentPage.value.icon)
const pageId = computed(() => currentPage.value.id)

const tickerItems = ref([
  { symbol: 'SH', name: '上证指数', price: 3085.24, change: 0.85 },
  { symbol: 'SZ', name: '深证成指', price: 9876.54, change: -0.32 },
  { symbol: 'CY', name: '创业板指', price: 1956.78, change: 1.24 },
  { symbol: 'HSI', name: '恒生指数', price: 16543.21, change: -0.15 },
  { symbol: 'IXIC', name: '纳斯达克', price: 15678.90, change: 2.34 },
])

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function toggleNotifications() {
  emit('toggleNotifications')
}

onMounted(() => {
  updateTime()
  timeInterval = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<style scoped>
.top-bar {
  height: 64px;
  background: linear-gradient(180deg, var(--bg-deep) 0%, var(--bg-layer) 100%);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  position: sticky;
  top: 0;
  z-index: 50;
}

/* 面包屑 */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.breadcrumb-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--neon-cyan-dim);
  border: 1px solid var(--neon-cyan);
  color: var(--neon-cyan);
  font-size: 1rem;
  text-shadow: 0 0 10px var(--neon-cyan);
}

.breadcrumb-content {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.page-id {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.page-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

/* 行情滚动 */
.market-ticker {
  flex: 1;
  max-width: 600px;
  margin: 0 2rem;
  overflow: hidden;
  position: relative;
}

.market-ticker::before,
.market-ticker::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  width: 60px;
  z-index: 2;
  pointer-events: none;
}

.market-ticker::before {
  left: 0;
  background: linear-gradient(90deg, var(--bg-layer), transparent);
}

.market-ticker::after {
  right: 0;
  background: linear-gradient(-90deg, var(--bg-layer), transparent);
}

.ticker-track {
  display: flex;
  gap: 2rem;
  animation: ticker-scroll 20s linear infinite;
}

@keyframes ticker-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  white-space: nowrap;
  flex-shrink: 0;
}

.ticker-symbol {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

.ticker-price {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.ticker-change {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.change-icon {
  font-size: 0.5rem;
}

.ticker-item.bull {
  border-color: rgba(0, 240, 255, 0.3);
}

.ticker-item.bull .ticker-change {
  color: var(--signal-buy);
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

.ticker-item.bear {
  border-color: rgba(255, 0, 170, 0.3);
}

.ticker-item.bear .ticker-change {
  color: var(--signal-sell);
  text-shadow: 0 0 10px rgba(255, 0, 170, 0.5);
}

/* 右侧操作区 */
.top-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

/* 时间显示 */
.time-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.time-value {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 600;
  color: var(--neon-amber);
  letter-spacing: 0.1em;
  text-shadow: 0 0 10px rgba(255, 184, 0, 0.3);
}

.time-label {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.15em;
  color: var(--text-muted);
}

/* 分隔线 */
.action-divider {
  width: 1px;
  height: 24px;
  background: var(--border-medium);
}

/* 赛博按钮 */
.cyber-icon-btn {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface);
  border: 1px solid var(--border-medium);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.cyber-icon-btn:hover {
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
}

.btn-glow {
  position: absolute;
  inset: 0;
  background: var(--neon-cyan);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.cyber-icon-btn:hover .btn-glow {
  opacity: 0.1;
}

.btn-icon {
  font-size: 1rem;
  z-index: 1;
}

.btn-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--neon-magenta);
  color: var(--bg-void);
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 700;
  border-radius: 50%;
  box-shadow: 0 0 10px var(--neon-magenta);
  animation: pulse-badge 2s ease-in-out infinite;
}

@keyframes pulse-badge {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

/* 用户菜单 */
.user-menu {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  padding: 0.5rem;
  border: 1px solid transparent;
  transition: all 0.3s ease;
}

.user-menu:hover {
  background: var(--bg-surface);
  border-color: var(--border-subtle);
}

.user-avatar {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--neon-purple), var(--neon-magenta));
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-primary);
}

.avatar-ring {
  position: absolute;
  inset: -2px;
  border: 1px solid var(--neon-cyan);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.user-menu:hover .avatar-ring {
  opacity: 1;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.user-role {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: var(--neon-cyan);
}

/* 响应式 */
@media (max-width: 1200px) {
  .market-ticker {
    display: none;
  }
}

@media (max-width: 768px) {
  .top-bar {
    padding: 0 1rem;
  }

  .user-info,
  .time-display {
    display: none;
  }
}
</style>
