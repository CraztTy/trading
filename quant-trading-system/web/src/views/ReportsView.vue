<template>
  <div class="reports-view">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">研究报告</h1>
        <p class="page-subtitle">查看交易分析报告</p>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
        />
      </div>
    </div>

    <div class="reports-grid">
      <div class="report-card performance">
        <div class="card-header">
          <h3>收益分析</h3>
          <span class="period">本月</span>
        </div>
        <div class="performance-chart">
          <div class="chart-placeholder">
            <div class="mock-chart">
              <div class="bar" v-for="i in 7" :key="i" :style="{ height: `${Math.random() * 60 + 20}%` }"></div>
            </div>
          </div>
        </div>
        <div class="performance-summary">
          <div class="summary-item">
            <span class="label">总收益率</span>
            <span class="value up">+12.45%</span>
          </div>
          <div class="summary-item">
            <span class="label">跑赢大盘</span>
            <span class="value up">+8.32%</span>
          </div>
        </div>
      </div>

      <div class="report-card trades">
        <div class="card-header">
          <h3>交易统计</h3>
        </div>
        <div class="stats-list">
          <div class="stat-row">
            <span class="stat-label">总交易次数</span>
            <span class="stat-value">48</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">盈利次数</span>
            <span class="stat-value up">32</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">亏损次数</span>
            <span class="stat-value down">16</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">胜率</span>
            <span class="stat-value">66.7%</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">平均盈利</span>
            <span class="stat-value up">+¥2,450</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">平均亏损</span>
            <span class="stat-value down">-¥980</span>
          </div>
        </div>
      </div>

      <div class="report-card distribution">
        <div class="card-header">
          <h3>收益分布</h3>
        </div>
        <div class="distribution-chart">
          <div class="pie-chart">
            <div class="pie-segment profit" style="--percentage: 70">70%</div>
            <div class="pie-segment loss" style="--percentage: 30">30%</div>
          </div>
          <div class="legend">
            <div class="legend-item">
              <span class="dot profit"></span>
              <span>盈利交易</span>
            </div>
            <div class="legend-item">
              <span class="dot loss"></span>
              <span>亏损交易</span>
            </div>
          </div>
        </div>
      </div>

      <div class="report-card history">
        <div class="card-header">
          <h3>近期交易</h3>
        </div>
        <div class="trade-list">
          <div class="trade-item" v-for="i in 5" :key="i">
            <div class="trade-info">
              <span class="trade-name">{{ ['贵州茅台', '宁德时代', '平安银行', '五粮液', '比亚迪'][i-1] }}</span>
              <span class="trade-date">2024-01-{{ 10 + i }}</span>
            </div>
            <div class="trade-result" :class="i % 2 === 0 ? 'up' : 'down'">
              {{ i % 2 === 0 ? '+' : '-' }}¥{{ (Math.random() * 5000 + 1000).toFixed(0) }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const dateRange = ref([])
</script>

<style scoped lang="scss">
.reports-view {
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

.reports-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-5);
}

.report-card {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-4);

    h3 {
      font-size: var(--text-base);
      font-weight: 600;
      color: var(--text-primary);
    }

    .period {
      font-size: var(--text-xs);
      color: var(--text-muted);
      padding: 2px 8px;
      background: var(--bg-hover);
      border-radius: var(--radius-sm);
    }
  }
}

.performance-chart {
  height: 150px;
  margin-bottom: var(--space-4);

  .chart-placeholder {
    height: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .mock-chart {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 100%;

    .bar {
      width: 30px;
      background: var(--accent-gold);
      border-radius: 4px 4px 0 0;
      opacity: 0.8;
      transition: all 0.3s;

      &:hover {
        opacity: 1;
      }
    }
  }
}

.performance-summary {
  display: flex;
  gap: var(--space-4);

  .summary-item {
    flex: 1;
    text-align: center;
    padding: var(--space-3);
    background: var(--bg-tertiary);
    border-radius: var(--radius-md);

    .label {
      display: block;
      font-size: var(--text-xs);
      color: var(--text-muted);
      margin-bottom: 4px;
    }

    .value {
      font-family: var(--font-mono);
      font-size: var(--text-lg);
      font-weight: 700;

      &.up { color: var(--accent-red); }
      &.down { color: var(--accent-green); }
    }
  }
}

.stats-list {
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--border-primary);

    &:last-child {
      border-bottom: none;
    }

    .stat-label {
      font-size: var(--text-sm);
      color: var(--text-secondary);
    }

    .stat-value {
      font-family: var(--font-mono);
      font-size: var(--text-base);
      font-weight: 600;
      color: var(--text-primary);

      &.up { color: var(--accent-red); }
      &.down { color: var(--accent-green); }
    }
  }
}

.distribution-chart {
  display: flex;
  align-items: center;
  gap: var(--space-6);

  .pie-chart {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: conic-gradient(
      var(--accent-red) 0% 70%,
      var(--accent-green) 70% 100%
    );
    position: relative;

    &::after {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 70px;
      height: 70px;
      background: var(--bg-card);
      border-radius: 50%;
    }
  }

  .legend {
    .legend-item {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      margin-bottom: var(--space-2);
      font-size: var(--text-sm);
      color: var(--text-secondary);

      .dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;

        &.profit {
          background: var(--accent-red);
        }

        &.loss {
          background: var(--accent-green);
        }
      }
    }
  }
}

.trade-list {
  .trade-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--border-primary);

    &:last-child {
      border-bottom: none;
    }

    .trade-info {
      display: flex;
      flex-direction: column;

      .trade-name {
        font-size: var(--text-sm);
        font-weight: 500;
        color: var(--text-primary);
      }

      .trade-date {
        font-size: var(--text-xs);
        color: var(--text-muted);
      }
    }

    .trade-result {
      font-family: var(--font-mono);
      font-size: var(--text-base);
      font-weight: 600;

      &.up { color: var(--accent-red); }
      &.down { color: var(--accent-green); }
    }
  }
}

@media (max-width: 1024px) {
  .reports-grid {
    grid-template-columns: 1fr;
  }
}
</style>
