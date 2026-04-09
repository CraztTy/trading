<template>
  <div class="panel">
    <div class="panel-header">
      <h3 class="panel-title">最新信号</h3>
      <span class="panel-badge live">实时</span>
    </div>
    <div class="panel-content">
      <div class="signals-list">
        <div v-for="signal in signals" :key="signal.id" class="signal-item" :class="signal.type">
          <div class="signal-icon">{{ signal.type === 'buy' ? '▲' : signal.type === 'sell' ? '▼' : '◆' }}</div>
          <div class="signal-content">
            <span class="signal-symbol">{{ signal.symbol }}</span>
            <span class="signal-action">{{ signal.action }}</span>
            <span class="signal-strategy">{{ signal.strategy }}</span>
          </div>
          <span class="signal-time">{{ signal.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const signals = ref([
  { id: 1, type: 'buy', symbol: '600519.SH', action: '买入信号', strategy: '均线突破策略', time: '09:45:23' },
  { id: 2, type: 'sell', symbol: '300750.SZ', action: '卖出信号', strategy: '止盈策略', time: '09:42:15' },
  { id: 3, type: 'buy', symbol: '000858.SZ', action: '买入信号', strategy: 'MACD金叉', time: '09:38:42' },
  { id: 4, type: 'hold', symbol: '000333.SZ', action: '持仓信号', strategy: '趋势跟踪', time: '09:35:18' },
])
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

.panel-badge.live {
  font-size: 0.6875rem;
  padding: 0.25rem 0.5rem;
  background: var(--accent-danger);
  color: white;
  border-radius: 0.25rem;
  animation: pulse 2s infinite;
}

.panel-content {
  padding: 1.5rem;
}

.signals-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.signal-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-tertiary);
  border-radius: 0.5rem;
  border-left: 3px solid transparent;
  transition: all 0.15s ease;
}

.signal-item:hover {
  background: var(--bg-hover);
}

.signal-item.buy {
  border-left-color: var(--accent-success);
}

.signal-item.sell {
  border-left-color: var(--accent-danger);
}

.signal-item.hold {
  border-left-color: var(--accent-secondary);
}

.signal-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.signal-item.buy .signal-icon {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.signal-item.sell .signal-icon {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.signal-item.hold .signal-icon {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-secondary);
}

.signal-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.signal-symbol {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.signal-action {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.signal-strategy {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.signal-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6875rem;
  color: var(--text-muted);
}
</style>
