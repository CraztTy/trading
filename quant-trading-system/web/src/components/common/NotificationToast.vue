<template>
  <div class="notification-container">
    <TransitionGroup name="notification">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="notification-item"
        :class="notification.type"
      >
        <div class="notification-icon">
          {{ getIcon(notification.type) }}
        </div>
        <div class="notification-content">
          <div class="notification-title">{{ notification.title }}</div>
          <div class="notification-message">{{ notification.message }}</div>
        </div>
        <button class="notification-close" @click="remove(notification.id)">
          ✕
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Notification {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  duration?: number
}

const notifications = ref<Notification[]>([])

function getIcon(type: string) {
  const icons: Record<string, string> = {
    success: '✓',
    warning: '⚠',
    error: '✕',
    info: 'ℹ'
  }
  return icons[type] || '•'
}

function add(notification: Omit<Notification, 'id'>) {
  const id = Date.now().toString()
  notifications.value.push({ ...notification, id })

  // 自动移除
  setTimeout(() => {
    remove(id)
  }, notification.duration || 5000)
}

function remove(id: string) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

// 暴露方法给外部使用
defineExpose({
  add,
  remove
})
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 400px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.notification-item.success {
  border-left: 3px solid var(--accent-success);
}

.notification-item.warning {
  border-left: 3px solid var(--accent-warning);
}

.notification-item.error {
  border-left: 3px solid var(--accent-danger);
}

.notification-item.info {
  border-left: 3px solid var(--accent-secondary);
}

.notification-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.notification-item.success .notification-icon {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.notification-item.warning .notification-icon {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.notification-item.error .notification-icon {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.notification-item.info .notification-icon {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-secondary);
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.notification-message {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.notification-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.notification-close:hover {
  color: var(--text-primary);
}

/* 过渡动画 */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
