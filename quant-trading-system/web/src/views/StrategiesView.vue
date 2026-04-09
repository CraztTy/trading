<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">策略管理</h1>
      <div class="page-actions">
        <button class="btn btn-secondary">导入策略</button>
        <button class="btn btn-primary">
          <span class="btn-icon">+</span>
          新建策略
        </button>
      </div>
    </div>

    <div class="strategies-grid">
      <div v-for="strategy in strategies" :key="strategy.id" class="strategy-card" :class="{ featured: strategy.featured }">
        <div class="strategy-card-header">
          <div class="strategy-icon">{{ strategy.icon }}</div>
          <div class="strategy-meta">
            <span class="strategy-name">{{ strategy.name }}</span>
            <span class="strategy-id">{{ strategy.id }}</span>
          </div>
          <span class="status-badge" :class="strategy.active ? 'running' : 'stopped'">
            {{ strategy.active ? '运行中' : '已停止' }}
          </span>
        </div>
        <div class="strategy-card-body">
          <div class="strategy-stats">
            <div class="stat">
              <span class="stat-label">累计收益</span>
              <span class="stat-value" :class="{ positive: strategy.return > 0 }">{{ strategy.return > 0 ? '+' : '' }}{{ strategy.return }}%</span>
            </div>
            <div class="stat">
              <span class="stat-label">胜率</span>
              <span class="stat-value">{{ strategy.winRate }}%</span>
            </div>
            <div class="stat">
              <span class="stat-label">最大回撤</span>
              <span class="stat-value negative">{{ strategy.drawdown }}%</span>
            </div>
            <div class="stat">
              <span class="stat-label">夏普比率</span>
              <span class="stat-value">{{ strategy.sharpe }}</span>
            </div>
          </div>
        </div>
        <div class="strategy-card-footer">
          <div class="strategy-tags">
            <span v-for="tag in strategy.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <div class="strategy-actions">
            <button class="btn-icon-only" title="编辑">✎</button>
            <button class="btn-icon-only" title="暂停">⏸</button>
            <button class="btn-icon-only danger" title="删除">✕</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const strategies = [
  { id: 'strategy_001', name: '双均线突破', icon: '⚡', featured: true, active: true, return: 24.5, winRate: 62.3, drawdown: -5.8, sharpe: 1.92, tags: ['趋势跟踪', '技术面'] },
  { id: 'strategy_002', name: 'MACD动量', icon: '◈', featured: false, active: true, return: 18.2, winRate: 58.7, drawdown: -7.2, sharpe: 1.65, tags: ['动量', '技术面'] },
  { id: 'strategy_003', name: '布林带均值回归', icon: '◉', featured: false, active: true, return: 31.8, winRate: 71.2, drawdown: -4.5, sharpe: 2.34, tags: ['均值回归', '技术面'] },
]
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.page-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
}

.page-actions {
  display: flex;
  gap: 1rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.btn-primary {
  background: var(--accent-primary);
  color: var(--bg-primary);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1.5rem;
}

.strategy-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
  transition: all 0.25s ease;
}

.strategy-card:hover {
  border-color: var(--border-secondary);
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
}

.strategy-card.featured {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 1px var(--accent-primary);
}

.strategy-card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-primary);
}

.strategy-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border-radius: 0.5rem;
  font-size: 1.25rem;
}

.strategy-card.featured .strategy-icon {
  background: var(--accent-primary);
  color: var(--bg-primary);
}

.strategy-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.strategy-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6875rem;
  color: var(--text-muted);
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

.strategy-card-body {
  padding: 1.5rem;
}

.strategy-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
}

.stat-value.positive {
  color: var(--accent-success);
}

.stat-value.negative {
  color: var(--accent-danger);
}

.strategy-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-primary);
}

.strategy-tags {
  display: flex;
  gap: 0.5rem;
}

.tag {
  padding: 0.25rem 0.5rem;
  background: var(--bg-tertiary);
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  color: var(--text-secondary);
}

.strategy-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon-only {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-icon-only:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-icon-only.danger:hover {
  background: var(--accent-danger);
  color: white;
}
</style>
