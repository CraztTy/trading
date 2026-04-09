<template>
  <div class="panel">
    <div class="panel-header">
      <h3 class="panel-title">策略状态</h3>
      <span class="panel-badge">3 运行中</span>
    </div>
    <div class="panel-content">
      <div class="strategies-list">
        <div v-for="strategy in strategies" :key="strategy.id" class="strategy-item" :class="{ active: strategy.active }">
          <div class="strategy-info">
            <span class="strategy-name">{{ strategy.name }}</span>
            <span class="strategy-desc">{{ strategy.desc }}</span>
          </div>
          <div class="strategy-status">
            <span class="status-badge" :class="strategy.active ? 'running' : 'stopped'">
              {{ strategy.active ? '运行中' : '已停止' }}
            </span>
            <span v-if="strategy.return" class="strategy-return" :class="{ positive: strategy.return > 0 }">
              {{ strategy.return > 0 ? '+' : '' }}{{ strategy.return }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const strategies = [
  { id: 1, name: '双均线突破', desc: 'MA5/MA20交叉策略', active: true, return: 12.5 },
  { id: 2, name: 'MACD动量', desc: 'MACD柱状图动量策略', active: true, return: 8.3 },
  { id: 3, name: '布林带均值回归', desc: '布林带突破回归策略', active: true, return: 15.2 },
  { id: 4, name: 'RSI超买超卖', desc: 'RSI极端值反转策略', active: false, return: null },
]
</script>

<style scoped>
.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.panel-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-badge {
  font-size: 0.6875rem;
  padding: 0.25rem 0.5rem;
  background: var(--bg-elevated);
  border-radius: 0.25rem;
  color: var(--text-secondary);
}

.panel-content {
  padding: 1.5rem;
}

.strategies-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.strategy-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--bg-tertiary);
  border-radius: 0.5rem;
  border-left: 3px solid var(--border-primary);
  transition: all 0.15s ease;
}

.strategy-item.active {
  border-left-color: var(--accent-success);
}

.strategy-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.strategy-name {
  font-weight: 500;
  color: var(--text-primary);
}

.strategy-desc {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.strategy-status {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  font-weight: 500;
}

.status-badge.running {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.status-badge.stopped {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

.strategy-return {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
}

.strategy-return.positive {
  color: var(--accent-success);
}
</style>
