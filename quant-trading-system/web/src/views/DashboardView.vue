<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">概览面板</h1>
      <div class="page-actions">
        <button class="btn btn-secondary">
          <span class="btn-icon">↻</span>
          刷新数据
        </button>
        <button class="btn btn-primary">
          <span class="btn-icon">+</span>
          新建策略
        </button>
      </div>
    </div>

    <div class="metrics-grid">
      <MetricCard
        v-for="metric in metrics"
        :key="metric.label"
        :label="metric.label"
        :value="metric.value"
        :trend="metric.trend"
        :subtext="metric.subtext"
        :large="metric.large"
        :positive="metric.positive"
        :negative="metric.negative"
      />
    </div>

    <div class="dashboard-grid">
      <div class="panel chart-panel">
        <div class="panel-header">
          <h3 class="panel-title">资产净值走势</h3>
          <div class="panel-actions">
            <button
              v-for="range in timeRanges"
              :key="range"
              class="panel-btn"
              :class="{ active: selectedRange === range }"
              @click="selectedRange = range"
            >
              {{ range }}
            </button>
          </div>
        </div>
        <div class="panel-content">
          <EquityChart />
        </div>
      </div>

      <PositionsPanel />
      <SignalsPanel />
      <StrategiesPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MetricCard from '@/components/common/MetricCard.vue'
import EquityChart from '@/components/charts/EquityChart.vue'
import PositionsPanel from '@/components/dashboard/PositionsPanel.vue'
import SignalsPanel from '@/components/dashboard/SignalsPanel.vue'
import StrategiesPanel from '@/components/dashboard/StrategiesPanel.vue'

const selectedRange = ref('1D')
const timeRanges = ['1D', '1W', '1M', '1Y', 'ALL']

const metrics = ref([
  {
    label: '总资产',
    value: '¥1,245,890.50',
    trend: '+5.2%',
    subtext: '初始资金: ¥1,000,000.00',
    large: true,
    positive: true,
  },
  {
    label: '今日盈亏',
    value: '+¥29,245.80',
    trend: '+2.4%',
    subtext: '日收益率: +2.35%',
    positive: true,
  },
  {
    label: '累计收益',
    value: '+¥245,890.50',
    trend: '+24.6%',
    subtext: '年化收益: +18.2%',
    positive: true,
  },
  {
    label: '夏普比率',
    value: '1.84',
    trend: '0.0',
    subtext: '风险调整后收益',
  },
  {
    label: '最大回撤',
    value: '-8.50%',
    trend: '-8.5%',
    subtext: '历史最大回撤',
    negative: true,
  },
  {
    label: '胜率',
    value: '58.4%',
    trend: '+1.2%',
    subtext: '总交易: 142笔',
  },
])
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

.btn-primary:hover {
  background: #fbbf24;
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--border-secondary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  grid-template-rows: auto auto;
  gap: 1.5rem;
}

.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
}

.panel:hover {
  border-color: var(--border-secondary);
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

.panel-actions {
  display: flex;
  gap: 0.25rem;
}

.panel-btn {
  padding: 0.25rem 0.5rem;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.6875rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.panel-btn:hover,
.panel-btn.active {
  background: var(--accent-primary);
  color: var(--bg-primary);
  border-color: var(--accent-primary);
}

.chart-panel {
  grid-row: span 2;
}

.chart-panel .panel-content {
  height: 400px;
  padding: 1rem;
}

@media (max-width: 1400px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .chart-panel {
    grid-row: span 1;
  }
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
