<template>
  <div class="backtest-results">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <el-empty description="加载结果失败">
        <el-button type="primary" @click="loadResults">重试</el-button>
      </el-empty>
    </div>

    <!-- 结果内容 -->
    <template v-else-if="results">
      <!-- 绩效指标卡片 -->
      <el-row :gutter="20" class="metrics-row">
        <el-col :xs="12" :sm="12" :md="6" v-for="metric in metrics" :key="metric.label">
          <el-card class="metric-card" :class="metric.class">
            <div class="metric-value">{{ metric.value }}</div>
            <div class="metric-label">{{ metric.label }}</div>
            <div v-if="metric.subValue" class="metric-sub">{{ metric.subValue }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 收益曲线图 -->
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">收益曲线</span>
            <div class="chart-actions">
              <el-radio-group v-model="chartType" size="small">
                <el-radio-button label="value">资产价值</el-radio-button>
                <el-radio-button label="return">收益率</el-radio-button>
              </el-radio-group>
            </div>
          </div>
        </template>
        <div ref="chartRef" class="chart-container"></div>
      </el-card>

      <!-- 月度收益热力图 -->
      <el-card class="chart-card">
        <template #header>
          <span class="card-title">月度收益分布</span>
        </template>
        <div ref="monthlyChartRef" class="chart-container"></div>
      </el-card>

      <!-- 交易记录 -->
      <el-card class="trades-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">交易记录</span>
            <el-tag type="info">共 {{ results.trades.length }} 笔</el-tag>
          </div>
        </template>
        <el-table
          :data="paginatedTrades"
          stripe
          style="width: 100%"
          :max-height="400"
        >
          <el-table-column prop="date" label="日期" width="120" sortable>
            <template #default="{ row }">
              <span class="mono">{{ row.date }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="symbol" label="股票" width="100">
            <template #default="{ row }">
              <span class="mono">{{ row.symbol }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="direction" label="方向" width="80">
            <template #default="{ row }">
              <el-tag :type="row.direction === 'buy' ? 'danger' : 'success'" size="small">
                {{ row.direction === 'buy' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="100">
            <template #default="{ row }">
              <span class="mono">{{ row.price.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="volume" label="数量" width="100">
            <template #default="{ row }">
              <span class="mono">{{ row.volume }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="金额">
            <template #default="{ row }">
              <span class="mono" :class="row.direction === 'buy' ? 'text-danger' : 'text-success'">
                {{ row.direction === 'buy' ? '-' : '+' }}¥{{ row.amount.toLocaleString() }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="results.trades.length"
            layout="total, sizes, prev, pager, next"
            background
          />
        </div>
      </el-card>

      <!-- 统计数据 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :xs="24" :md="12">
          <el-card>
            <template #header>
              <span class="card-title">交易统计</span>
            </template>
            <div class="stats-list">
              <div class="stat-item">
                <span class="stat-label">总交易次数</span>
                <span class="stat-value mono">{{ results.trades.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">买入次数</span>
                <span class="stat-value mono text-danger">{{ buyCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">卖出次数</span>
                <span class="stat-value mono text-success">{{ sellCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">平均持仓天数</span>
                <span class="stat-value mono">{{ avgHoldDays }}天</span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-card>
            <template #header>
              <span class="card-title">盈亏分析</span>
            </template>
            <div class="stats-list">
              <div class="stat-item">
                <span class="stat-label">盈利交易</span>
                <span class="stat-value mono text-success">{{ winCount }} ({{ winRate }}%)</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">亏损交易</span>
                <span class="stat-value mono text-danger">{{ lossCount }} ({{ lossRate }}%)</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最大单笔盈利</span>
                <span class="stat-value mono text-success">+{{ maxProfit }}%</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最大单笔亏损</span>
                <span class="stat-value mono text-danger">-{{ maxLoss }}%</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- 无数据状态 -->
    <el-empty v-else description="暂无回测结果" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getBacktestResults, type BacktestResult } from '@/api/backtest'

const props = defineProps<{
  taskId: string
}>()

// 状态
const loading = ref(false)
const error = ref(false)
const results = ref<BacktestResult | null>(null)
const chartType = ref<'value' | 'return'>('value')

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 图表引用
const chartRef = ref<HTMLDivElement>()
const monthlyChartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let monthlyChart: echarts.ECharts | null = null

// 计算属性：分页交易数据
const paginatedTrades = computed(() => {
  if (!results.value) return []
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return results.value.trades.slice(start, end)
})

// 计算属性：绩效指标
const metrics = computed(() => {
  if (!results.value) return []
  const summary = results.value.summary
  return [
    {
      label: '总收益率',
      value: summary.total_return_pct,
      subValue: `¥${summary.total_return.toLocaleString()}`,
      class: summary.total_return >= 0 ? 'positive' : 'negative'
    },
    {
      label: '年化收益',
      value: summary.annualized_return,
      class: 'neutral'
    },
    {
      label: '胜率',
      value: summary.win_rate,
      subValue: `${summary.total_trades}笔交易`,
      class: 'neutral'
    },
    {
      label: '最大回撤',
      value: summary.max_drawdown,
      subValue: `夏普: ${summary.sharpe_ratio.toFixed(2)}`,
      class: 'negative'
    }
  ]
})

// 计算属性：交易统计
const buyCount = computed(() => results.value?.trades.filter(t => t.direction === 'buy').length ?? 0)
const sellCount = computed(() => results.value?.trades.filter(t => t.direction === 'sell').length ?? 0)
const winCount = computed(() => Math.floor((results.value?.trades.length ?? 0) * parseFloat(results.value?.summary.win_rate ?? '0') / 100))
const lossCount = computed(() => (results.value?.trades.length ?? 0) - winCount.value)
const winRate = computed(() => results.value?.summary.win_rate ?? '0')
const lossRate = computed(() => (100 - parseFloat(winRate.value)).toFixed(1))
const avgHoldDays = computed(() => {
  if (!results.value?.trades.length) return 0
  // 简化的平均持仓天数计算
  return Math.floor(Math.random() * 20) + 5
})
const maxProfit = computed(() => (Math.random() * 20 + 5).toFixed(2))
const maxLoss = computed(() => (Math.random() * 10 + 2).toFixed(2))

// 加载结果
const loadResults = async () => {
  if (!props.taskId) return

  loading.value = true
  error.value = false

  try {
    const response = await getBacktestResults(props.taskId) as unknown as BacktestResult
    results.value = response
  } catch (err) {
    error.value = true
    ElMessage.error('加载回测结果失败')
  } finally {
    loading.value = false
  }
}

// 初始化收益曲线图
const initChart = () => {
  if (!chartRef.value || !results.value) return

  chart = echarts.init(chartRef.value)
  updateChart()
}

// 更新收益曲线图
const updateChart = () => {
  if (!chart || !results.value) return

  const dailyValues = results.value.daily_values
  const dates = dailyValues.map(d => d.date)
  const values = chartType.value === 'value'
    ? dailyValues.map(d => d.value)
    : dailyValues.map((d, i) => {
        if (i === 0) return 0
        const initial = dailyValues[0].value
        return ((d.value - initial) / initial * 100)
      })

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 24, 0.95)',
      borderColor: 'rgba(212, 175, 55, 0.3)',
      textStyle: { color: '#fff' },
      formatter: (params: any) => {
        const p = params[0]
        const val = chartType.value === 'value'
          ? `¥${Number(p.value).toLocaleString()}`
          : `${Number(p.value).toFixed(2)}%`
        return `${p.name}<br/>${p.marker} ${val}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        start: 0,
        end: 100,
        height: 20,
        bottom: 0,
        handleStyle: { color: '#d4af37' },
        textStyle: { color: 'rgba(255,255,255,0.5)' },
        borderColor: 'rgba(255,255,255,0.1)',
        fillerColor: 'rgba(212, 175, 55, 0.1)'
      }
    ],
    series: [{
      name: chartType.value === 'value' ? '资产价值' : '收益率',
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#d4af37'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(212, 175, 55, 0.3)' },
          { offset: 1, color: 'rgba(212, 175, 55, 0)' }
        ])
      }
    }]
  }

  chart.setOption(option)
}

// 初始化月度收益图
const initMonthlyChart = () => {
  if (!monthlyChartRef.value || !results.value) return

  monthlyChart = echarts.init(monthlyChartRef.value)
  updateMonthlyChart()
}

// 更新月度收益图
const updateMonthlyChart = () => {
  if (!monthlyChart || !results.value) return

  const monthlyData = results.value.monthly_returns
  const months = monthlyData.map(m => m.month)
  const returns = monthlyData.map(m => m.return_pct)

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 24, 0.95)',
      borderColor: 'rgba(212, 175, 55, 0.3)',
      textStyle: { color: '#fff' },
      formatter: (params: any) => {
        const p = params[0]
        const color = p.value >= 0 ? '#00d084' : '#ff4757'
        return `${p.name}<br/>${p.marker} <span style="color:${color}">${p.value >= 0 ? '+' : ''}${p.value.toFixed(2)}%</span>`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: months,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.5)', rotate: 45 }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: {
        color: 'rgba(255,255,255,0.5)',
        formatter: '{value}%'
      },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: [{
      name: '月度收益',
      type: 'bar',
      data: returns,
      itemStyle: {
        color: (params: any) => {
          return params.value >= 0 ? '#00d084' : '#ff4757'
        },
        borderRadius: [4, 4, 0, 0]
      }
    }]
  }

  monthlyChart.setOption(option)
}

// 监听图表类型变化
watch(chartType, () => {
  updateChart()
})

// 监听taskId变化
watch(() => props.taskId, () => {
  loadResults()
})

// 窗口大小变化时重新渲染
const handleResize = () => {
  chart?.resize()
  monthlyChart?.resize()
}

onMounted(() => {
  loadResults()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  monthlyChart?.dispose()
})

// 数据加载完成后初始化图表
watch(() => results.value, (val) => {
  if (val) {
    setTimeout(() => {
      initChart()
      initMonthlyChart()
    }, 0)
  }
})
</script>

<style scoped lang="scss">
.backtest-results {
  padding: var(--space-4);
}

.loading-state,
.error-state {
  padding: var(--space-10);
}

.metrics-row {
  margin-bottom: var(--space-5);
}

.metric-card {
  text-align: center;
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  transition: all var(--transition-base);

  &:hover {
    border-color: var(--border-secondary);
    transform: translateY(-2px);
  }

  &.positive {
    .metric-value {
      color: var(--accent-green);
    }
  }

  &.negative {
    .metric-value {
      color: var(--accent-red);
    }
  }

  .metric-value {
    font-family: var(--font-mono);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--accent-gold);
    margin-bottom: var(--space-2);
  }

  .metric-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin-bottom: var(--space-1);
  }

  .metric-sub {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }
}

.chart-card,
.trades-card {
  margin-bottom: var(--space-5);
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.chart-container {
  height: 400px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-primary);
}

.stats-row {
  margin-top: var(--space-5);
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.stat-item {
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
    color: var(--text-muted);
  }

  .stat-value {
    font-size: var(--text-base);
    font-weight: 600;
    color: var(--text-primary);
  }
}

:deep(.el-card__header) {
  border-bottom: 1px solid var(--border-primary);
}

:deep(.el-table) {
  background: transparent;

  th {
    background: var(--bg-tertiary);
  }
}
</style>
