<template>
  <div class="strategy-view">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">策略回测</h1>
        <p class="page-subtitle">回测您的交易策略</p>
      </div>
      <button class="create-btn">
        <el-icon><Plus /></el-icon>
        新建策略
      </button>
    </div>

    <div class="strategy-grid">
      <div v-for="strategy in strategies" :key="strategy.id" class="strategy-card">
        <div class="card-header">
          <h3 class="strategy-name">{{ strategy.name }}</h3>
          <span :class="['status-badge', strategy.status]">{{ strategy.statusText }}</span>
        </div>
        <p class="strategy-desc">{{ strategy.description }}</p>
        <div class="strategy-metrics">
          <div class="metric">
            <span class="label">年化收益</span>
            <span :class="['value', strategy.annualReturn >= 0 ? 'up' : 'down']">
              {{ strategy.annualReturn >= 0 ? '+' : '' }}{{ strategy.annualReturn }}%
            </span>
          </div>
          <div class="metric">
            <span class="label">夏普比率</span>
            <span class="value">{{ strategy.sharpe }}</span>
          </div>
          <div class="metric">
            <span class="label">最大回撤</span>
            <span class="value down">-{{ strategy.maxDrawdown }}%</span>
          </div>
        </div>
        <div class="card-actions">
          <button class="action-btn primary">运行回测</button>
          <button class="action-btn">编辑</button>
          <button class="action-btn">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'

const strategies = [
  {
    id: 1,
    name: '双均线策略',
    description: '基于5日和20日均线的金叉死叉交易信号',
    status: 'active',
    statusText: '运行中',
    annualReturn: 23.5,
    sharpe: 1.85,
    maxDrawdown: 12.3
  },
  {
    id: 2,
    name: 'MACD动量策略',
    description: '利用MACD指标的动量效应进行趋势跟踪',
    status: 'paused',
    statusText: '已暂停',
    annualReturn: 18.2,
    sharpe: 1.42,
    maxDrawdown: 15.6
  },
  {
    id: 3,
    name: '价值投资策略',
    description: '基于PE、PB估值指标的低估值选股策略',
    status: 'active',
    statusText: '运行中',
    annualReturn: 15.8,
    sharpe: 1.65,
    maxDrawdown: 8.2
  },
  {
    id: 4,
    name: '小市值策略',
    description: '选取市值最小的50只股票定期调仓',
    status: 'draft',
    statusText: '草稿',
    annualReturn: 28.5,
    sharpe: 1.22,
    maxDrawdown: 22.1
  }
]
</script>

<style scoped lang="scss">
.strategy-view {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);

  .page-title {
    font-family: var(--font-display);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: var(--space-2);
  }

  .page-subtitle {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
}

.create-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--accent-gold);
  border: none;
  border-radius: var(--radius-md);
  color: var(--bg-primary);
  font-weight: 600;
  cursor: pointer;

  &:hover {
    box-shadow: var(--shadow-gold);
  }
}

.strategy-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
}

.strategy-card {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  transition: all var(--transition-base);

  &:hover {
    border-color: var(--accent-gold);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-3);
  }

  .strategy-name {
    font-size: var(--text-lg);
    font-weight: 600;
    color: var(--text-primary);
  }

  .status-badge {
    padding: 4px 12px;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    font-weight: 500;

    &.active {
      background: rgba(0, 208, 132, 0.15);
      color: var(--accent-green);
    }

    &.paused {
      background: rgba(255, 149, 0, 0.15);
      color: var(--accent-gold);
    }

    &.draft {
      background: var(--bg-hover);
      color: var(--text-muted);
    }
  }

  .strategy-desc {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-bottom: var(--space-4);
  }

  .strategy-metrics {
    display: flex;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
    padding: var(--space-3);
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);

    .metric {
      flex: 1;
      text-align: center;

      .label {
        display: block;
        font-size: var(--text-xs);
        color: var(--text-muted);
        margin-bottom: 4px;
      }

      .value {
        font-family: var(--font-mono);
        font-size: var(--text-lg);
        font-weight: 600;

        &.up { color: var(--accent-red); }
        &.down { color: var(--accent-green); }
      }
    }
  }

  .card-actions {
    display: flex;
    gap: var(--space-2);

    .action-btn {
      flex: 1;
      padding: var(--space-2);
      background: var(--bg-hover);
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      font-size: var(--text-sm);
      cursor: pointer;
      transition: all var(--transition-fast);

      &:hover {
        border-color: var(--accent-gold);
        color: var(--accent-gold);
      }

      &.primary {
        background: var(--accent-gold);
        border-color: var(--accent-gold);
        color: var(--bg-primary);
      }
    }
  }
}

@media (max-width: 768px) {
  .strategy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
