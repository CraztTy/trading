<template>
  <div class="panel">
    <div class="panel-header">
      <h3 class="panel-title">当前持仓</h3>
      <span class="panel-badge">5 只股票</span>
    </div>
    <div class="panel-content">
      <div class="positions-list">
        <div v-for="position in positions" :key="position.symbol" class="position-item">
          <div class="position-info">
            <span class="position-symbol">{{ position.symbol }}</span>
            <span class="position-name">{{ position.name }}</span>
          </div>
          <div class="position-metrics">
            <span class="position-qty">{{ position.qty }}股</span>
            <span class="position-value">¥{{ position.value.toLocaleString() }}</span>
            <span class="position-pnl" :class="{ positive: position.pnl > 0, negative: position.pnl < 0 }">
              {{ position.pnl > 0 ? '+' : '' }}{{ position.pnl }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const positions = [
  { symbol: '600519.SH', name: '贵州茅台', qty: 100, value: 168500, pnl: 5.2 },
  { symbol: '000858.SZ', name: '五粮液', qty: 200, value: 45600, pnl: 3.1 },
  { symbol: '300750.SZ', name: '宁德时代', qty: 150, value: 32850, pnl: -1.2 },
  { symbol: '000333.SZ', name: '美的集团', qty: 300, value: 19800, pnl: 0.8 },
  { symbol: '002594.SZ', name: '比亚迪', qty: 80, value: 18400, pnl: 2.5 },
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

.positions-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.position-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--bg-tertiary);
  border-radius: 0.5rem;
  transition: all 0.15s ease;
}

.position-item:hover {
  background: var(--bg-hover);
}

.position-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.position-symbol {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.position-name {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.position-metrics {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
}

.position-qty {
  color: var(--text-secondary);
}

.position-value {
  color: var(--text-primary);
  font-weight: 500;
}

.position-pnl {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.position-pnl.positive {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.position-pnl.negative {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}
</style>
