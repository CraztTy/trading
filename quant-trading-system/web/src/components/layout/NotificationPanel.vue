<template>
  <div class="notification-panel" :class="{ open: isOpen }">
    <div class="notification-header">
      <h3>通知</h3>
      <button class="btn-text" @click="markAllRead">全部已读</button>
    </div>
    <div class="notification-list">
      <div v-for="notification in notifications" :key="notification.id" class="notification-item" :class="{ unread: !notification.read }">
        <div class="notification-icon" :class="notification.type">{{ getIcon(notification.type) }}</div>
        <div class="notification-content">
          <p class="notification-title">{{ notification.title }}</p>
          <p class="notification-desc">{{ notification.desc }}</p>
          <span class="notification-time">{{ notification.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const isOpen = ref(false)

const notifications = ref([
  { id: 1, type: 'buy', title: '买入信号触发', desc: '贵州茅台 (600519.SH) - 双均线突破策略', time: '2分钟前', read: false },
  { id: 2, type: 'risk', title: '风控提醒', desc: '单日亏损接近2%熔断线', time: '15分钟前', read: false },
  { id: 3, type: 'system', title: '回测完成', desc: '策略"MACD动量"回测已完成', time: '1小时前', read: true },
])

function getIcon(type: string) {
  const icons: Record<string, string> = {
    buy: '▲',
    sell: '▼',
    risk: '⚠',
    system: '◈'
  }
  return icons[type] || '◈'
}

function markAllRead() {
  notifications.value.forEach(n => n.read = true)
}

function toggle() {
  isOpen.value = !isOpen.value
}

defineExpose({ toggle })
</script>

<style scoped>
.notification-panel {
  position: fixed;
  top: 60px;
  right: -400px;
  width: 360px;
  height: calc(100vh - 60px);
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  z-index: 200;
  transition: right 0.25s ease;
  display: flex;
  flex-direction: column;
}

.notification-panel.open {
  right: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-primary);
}

.notification-header h3 {
  font-size: 1rem;
  font-weight: 600;
}

.btn-text {
  background: transparent;
  border: none;
  color: var(--accent-secondary);
  font-size: 0.75rem;
  cursor: pointer;
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.notification-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  transition: all 0.15s ease;
}

.notification-item:hover {
  background: var(--bg-tertiary);
}

.notification-item.unread {
  background: var(--bg-tertiary);
}

.notification-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.notification-icon.buy {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.notification-icon.risk {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.notification-icon.system {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-secondary);
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.notification-desc {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.notification-time {
  font-size: 0.6875rem;
  color: var(--text-muted);
}
</style>
