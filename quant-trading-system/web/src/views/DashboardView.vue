<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">实时监控您的投资组合与市场动态</p>
      </div>
      <div class="header-right">
        <div class="market-status">
          <span class="status-dot"></span>
          <span class="status-text">交易中</span>
          <span class="status-time">{{ currentTime }}</span>
        </div>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <div class="metrics-row">
      <div
        v-for="metric in metrics"
        :key="metric.title"
        class="metric-card"
        :class="`metric-${metric.color}`"
      >
        <div class="metric-header">
          <div class="metric-icon">
            <component :is="metric.icon" />
          </div>
          <div class="metric-trend" :class="metric.trend">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <path v-if="metric.trend === 'up'" d="M7 17l5-5 5 5M12 12V3" />
              <path v-else-if="metric.trend === 'down'" d="M7 7l5 5 5-5M12 12v9" />
              <path v-else d="M5 12h14" />
            </svg>
            <span>{{ metric.change }}</span>
          </div>
        </div>

        <div class="metric-value">
          <span class="value-prefix" v-if="metric.prefix">{{ metric.prefix }}</span>
          <span class="value-number">{{ metric.value }}</span>
        </div>

        <div class="metric-label">{{ metric.title }}</div>

        <div class="metric-footer">
          <span class="footer-text">{{ metric.footer }}></span>
        </div>
      </div>
    </div>

    <!-- 三省六部数据流监控 -->
    <ShengFlowMonitor />

    <!-- 主内容区 -->
    <div class="main-grid">
      <!-- 左侧：收益曲线 -->
      <div class="chart-section">
        <div class="section-header">
          <div class="header-title">
            <span class="title-icon">📈</span>
            <span>收益曲线</span>
          </div>
          <div class="time-tabs">
            <button
              v-for="tab in timeTabs"
              :key="tab.value"
              :class="['tab-btn', { active: activeTab === tab.value }]"
              @click="activeTab = tab.value"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div class="chart-container">
          <div ref="chartRef" class="chart"></div>
        </div>

        <div class="chart-stats">
          <div class="stat-item">
            <span class="stat-label">总收益率</span>
            <span class="stat-value text-up">+38.45%</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">夏普比率</span>
            <span class="stat-value">1.85</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">最大回撤</span>
            <span class="stat-value text-down">-8.32%</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">年化收益</span>
            <span class="stat-value text-up">+24.67%</span>
          </div>
        </div>
      </div>

      <!-- 右侧：持仓列表 -->
      <div class="positions-section">
        <div class="section-header">
          <div class="header-title">
            <span class="title-icon">💼</span>
            <span>持仓概览</span>
          </div>
          <button class="view-all-btn">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>

        <div class="positions-list">
          <div
            v-for="position in positions"
            :key="position.symbol"
            class="position-item"
          >
            <div class="position-info">
              <div class="stock-name">{{ position.name }}</div>
              <div class="stock-code">{{ position.symbol }}</div>
            </div>

            <div class="position-price">
              <div class="current-price" :class="getTrendClass(position)">
                ¥{{ position.currentPrice.toFixed(2) }}
              </div>
              <div class="position-qty">{{ position.quantity }}股</div>
            </div>

            <div class="position-pnl">
              <div class="pnl-value" :class="getPnlClass(position)">
                {{ position.unrealizedPnl >= 0 ? '+' : '' }}¥{{ formatNumber(position.unrealizedPnl) }}
              </div>
              <div class="pnl-percent" :class="getPnlClass(position)">
                {{ position.unrealizedPnlPct >= 0 ? '+' : '' }}{{ (position.unrealizedPnlPct * 100).toFixed(2) }}%
              </div>
            </div>
          </div>
        </div>

        <div class="positions-summary">
          <div class="summary-row">
            <span>持仓市值</span>
            <span class="summary-value">¥{{ formatNumber(900690) }}</span>
          </div>
          <div class="summary-row">
            <span>今日盈亏</span>
            <span class="summary-value text-up">+¥{{ formatNumber(8420) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部区域 -->
    <div class="bottom-grid">
      <!-- 订单簿 -->
      <div class="orderbook-section">
        <div class="section-header">
          <div class="header-title">
            <span class="title-icon">📊</span>
            <span>盘口数据</span>
            <span class="stock-tag">贵州茅台 600519</span>
          </div>
          <div class="current-price-display">
            <span class="price-label">最新价</span>
            <span class="price-value text-up">1,725.00</span>
            <span class="price-change">+1.45%</span>
          </div>
        </div>

        <div class="orderbook">
          <div class="book-header">
            <span>买/卖</span>
            <span>价格</span>
            <span>数量</span>
          </div>

          <!-- 卖盘 -->
          <div class="book-side sells">
            <div
              v-for="(level, i) in orderBook.asks"
              :key="`ask-${i}`"
              class="book-level"
            >
              <span class="level-side">卖{{ 5 - i }}</span>
              <span class="level-price text-down">{{ level.price.toFixed(2) }}</span>
              <div class="level-bar">
                <div class="bar-fill" :style="{ width: `${(level.volume / maxVolume) * 100}%` }"></div>
                <span class="bar-value">{{ level.volume }}</span>
              </div>
            </div>
          </div>

          <!-- 中间价格 -->
          <div class="book-spread">
            <span class="spread-label">价差</span>
            <span class="spread-value">{{ (orderBook.asks[0].price - orderBook.bids[0].price).toFixed(2) }}</span>
          </div>

          <!-- 买盘 -->
          <div class="book-side buys">
            <div
              v-for="(level, i) in orderBook.bids"
              :key="`bid-${i}`"
              class="book-level"
            >
              <span class="level-side">买{{ i + 1 }}</span>
              <span class="level-price text-up">{{ level.price.toFixed(2) }}</span>
              <div class="level-bar">
                <div class="bar-fill buy" :style="{ width: `${(level.volume / maxVolume) * 100}%` }"></div>
                <span class="bar-value">{{ level.volume }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI推荐 -->
      <div class="ai-section">
        <div class="section-header">
          <div class="header-title">
            <span class="title-icon">🤖</span>
            <span>AI 选股</span>
          </div>
          <span class="ai-badge">实时</span>
        </div>

        <div class="recommendations-list">
          <div
            v-for="rec in recommendations"
            :key="rec.symbol"
            class="rec-item"
          >
            <div class="rec-rank">
              <div class="rank-number" :class="getRankClass(rec.score)">{{ rec.score }}</div>
              <div class="rank-label">评分</div>
            </div>

            <div class="rec-info">
              <div class="rec-name">{{ rec.name }}</div>
              <div class="rec-symbol">{{ rec.symbol }}</div>
              <div class="rec-tags">
                <span v-for="tag in rec.tags" :key="tag" class="rec-tag">{{ tag }}</span>
              </div>
            </div>

            <div class="rec-reason">
              <span class="reason-label">{{ rec.reason }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import ShengFlowMonitor from '@/components/dashboard/ShengFlowMonitor.vue'
import * as echarts from 'echarts'
import {
  Wallet,
  TrendCharts,
  Money,
  Box,
  ArrowRight
} from '@element-plus/icons-vue'

// 当前时间
const currentTime = ref('')
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
setInterval(updateTime, 1000)
updateTime()

// 指标数据
const metrics = [
  {
    title: '总资产',
    value: '1,284,520',
    prefix: '¥',
    change: '+12.45%',
    trend: 'up' as const,
    footer: '较上月',
    icon: Wallet,
    color: 'gold'
  },
  {
    title: '今日盈亏',
    value: '+8,420',
    prefix: '¥',
    change: '+2.34%',
    trend: 'up' as const,
    footer: '日内收益',
    icon: TrendCharts,
    color: 'cyan'
  },
  {
    title: '可用资金',
    value: '345,200',
    prefix: '¥',
    change: '72%',
    trend: 'neutral' as const,
    footer: '仓位占比',
    icon: Money,
    color: 'green'
  },
  {
    title: '持仓市值',
    value: '900,690',
    prefix: '¥',
    change: '+5.67%',
    trend: 'up' as const,
    footer: '浮动盈亏',
    icon: Box,
    color: 'purple'
  },
  // 添加一个下跌的示例（用于展示UI）
  {
    title: '当日回撤',
    value: '-2,450',
    prefix: '¥',
    change: '-0.68%',
    trend: 'down' as const,
    footer: '最大回撤',
    icon: Box,
    color: 'red'
  }
]

// 时间标签
const timeTabs = [
  { label: '1D', value: '1d' },
  { label: '1W', value: '1w' },
  { label: '1M', value: '1m' },
  { label: 'YTD', value: 'ytd' },
  { label: 'ALL', value: 'all' }
]
const activeTab = ref('1d')

// 持仓数据
const positions = [
  {
    symbol: '600519.SH',
    name: '贵州茅台',
    quantity: 100,
    currentPrice: 1725.00,
    unrealizedPnl: 7500.00,
    unrealizedPnlPct: 0.0455
  },
  {
    symbol: '300750.SZ',
    name: '宁德时代',
    quantity: 500,
    currentPrice: 200.00,
    unrealizedPnl: 2500.00,
    unrealizedPnlPct: 0.0256
  },
  {
    symbol: '000001.SZ',
    name: '平安银行',
    quantity: 2000,
    currentPrice: 10.25,
    unrealizedPnl: -400.00,
    unrealizedPnlPct: -0.0191
  },
  {
    symbol: '000858.SZ',
    name: '五粮液',
    quantity: 300,
    currentPrice: 154.80,
    unrealizedPnl: 1890.00,
    unrealizedPnlPct: 0.0424
  },
  {
    symbol: '002594.SZ',
    name: '比亚迪',
    quantity: 200,
    currentPrice: 245.60,
    unrealizedPnl: -1200.00,
    unrealizedPnlPct: -0.0238
  }
]

// 订单簿数据
const orderBook = {
  asks: [
    { price: 1725.50, volume: 45 },
    { price: 1725.80, volume: 120 },
    { price: 1726.00, volume: 89 },
    { price: 1726.50, volume: 234 },
    { price: 1727.00, volume: 156 }
  ],
  bids: [
    { price: 1724.50, volume: 78 },
    { price: 1724.20, volume: 145 },
    { price: 1724.00, volume: 203 },
    { price: 1723.80, volume: 89 },
    { price: 1723.50, volume: 167 }
  ]
}

const maxVolume = computed(() => {
  const allVolumes = [...orderBook.asks, ...orderBook.bids].map(l => l.volume)
  return Math.max(...allVolumes)
})

// AI推荐
const recommendations = [
  {
    symbol: '002371.SZ',
    name: '北方华创',
    reason: '价值+成长',
    score: 92,
    tags: ['半导体', '设备龙头']
  },
  {
    symbol: '300760.SZ',
    name: '迈瑞医疗',
    reason: '质量因子',
    score: 88,
    tags: ['医疗器械', '龙头']
  },
  {
    symbol: '600900.SH',
    name: '长江电力',
    reason: '高股息',
    score: 85,
    tags: ['电力', '高分红']
  }
]

// 图表
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const data = Array.from({ length: 50 }, (_, i) => {
    const base = 1.0
    const trend = i * 0.008
    const noise = (Math.random() - 0.5) * 0.02
    return +(base + trend + noise).toFixed(4)
  })

  const option = {
    backgroundColor: 'transparent',
    grid: {
      top: 20,
      right: 20,
      bottom: 30,
      left: 60
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 50 }, (_, i) => i),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0.9,
      max: 1.5,
      axisLine: { show: false },
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.05)',
          type: 'dashed'
        }
      },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.4)',
        fontFamily: 'JetBrains Mono',
        fontSize: 11,
        formatter: (value: number) => `${(value * 100 - 100).toFixed(0)}%`
      }
    },
    series: [{
      data,
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        color: '#d4af37',
        width: 2,
        shadowColor: 'rgba(212, 175, 55, 0.5)',
        shadowBlur: 10
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(212, 175, 55, 0.3)' },
            { offset: 1, color: 'rgba(212, 175, 55, 0)' }
          ]
        }
      }
    }],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 17, 24, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: {
        color: '#fff',
        fontFamily: 'JetBrains Mono'
      },
      formatter: (params: any) => {
        const value = params[0].value
        return `收益率: +${((value - 1) * 100).toFixed(2)}%`
      }
    }
  }

  chart.setOption(option)
}

// 辅助函数
const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN')
}

const getTrendClass = (position: any) => {
  return position.currentPrice >= position.avgCost ? 'text-up' : 'text-down'
}

const getPnlClass = (position: any) => {
  return position.unrealizedPnl >= 0 ? 'text-up' : 'text-down'
}

const getRankClass = (score: number) => {
  if (score >= 90) return 'rank-excellent'
  if (score >= 80) return 'rank-good'
  return 'rank-normal'
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', () => chart?.resize())
})
</script>

<style scoped lang="scss">
.dashboard {
  max-width: 1600px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 页面标题
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.market-status {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);

  .status-dot {
    width: 8px;
    height: 8px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 10px var(--accent-green);
  }

  .status-text {
    font-size: var(--text-sm);
    font-weight: 500;
    color: var(--accent-green);
  }

  .status-time {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--text-secondary);
    padding-left: var(--space-3);
    border-left: 1px solid var(--border-primary);
  }
}

// 指标卡片行
.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.metric-card {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--gradient-gold);
    opacity: 0;
    transition: opacity var(--transition-fast);
  }

  &:hover {
    border-color: var(--border-secondary);
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);

    &::before {
      opacity: 1;
    }
  }

  &.metric-cyan::before {
    background: linear-gradient(90deg, var(--accent-cyan), transparent);
  }

  &.metric-green::before {
    background: linear-gradient(90deg, var(--accent-green), transparent);
  }

  &.metric-purple::before {
    background: linear-gradient(90deg, var(--accent-purple), transparent);
  }
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.metric-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--accent-gold);
  font-size: var(--text-lg);
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;

  &.up {
    color: var(--accent-green);
    background: rgba(0, 208, 132, 0.1);
  }

  &.down {
    color: var(--accent-red);
    background: rgba(255, 71, 87, 0.1);
  }

  &.neutral {
    color: var(--text-muted);
    background: var(--bg-hover);
  }
}

.metric-value {
  margin-bottom: var(--space-2);

  .value-prefix {
    font-family: var(--font-mono);
    font-size: var(--text-lg);
    color: var(--text-secondary);
    margin-right: 2px;
  }

  .value-number {
    font-family: var(--font-mono);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
  }
}

.metric-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.metric-footer {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-primary);

  .footer-text {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

// 主网格
.main-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}

// 通用区块头部
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-primary);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);

  .title-icon {
    font-size: var(--text-lg);
  }
}

// 图表区块
.chart-section {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.time-tabs {
  display: flex;
  gap: var(--space-1);
  background: var(--bg-tertiary);
  padding: 4px;
  border-radius: var(--radius-md);
}

.tab-btn {
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--text-primary);
  }

  &.active {
    background: var(--bg-elevated);
    color: var(--accent-gold);
    box-shadow: var(--shadow-sm);
  }
}

.chart-container {
  padding: var(--space-5);
}

.chart {
  height: 280px;
}

.chart-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.2);
}

.stat-item {
  text-align: center;

  .stat-label {
    display: block;
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-bottom: var(--space-1);
  }

  .stat-value {
    font-family: var(--font-mono);
    font-size: var(--text-lg);
    font-weight: 700;
  }
}

// 持仓区块
.positions-section {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.view-all-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  .el-icon {
    font-size: var(--text-xs);
  }

  &:hover {
    border-color: var(--accent-gold);
    color: var(--accent-gold);
  }
}

.positions-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.position-item {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }

  &:not(:last-child) {
    border-bottom: 1px solid var(--border-primary);
  }
}

.position-info {
  .stock-name {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 2px;
  }

  .stock-code {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

.position-price {
  text-align: right;

  .current-price {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .position-qty {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

.position-pnl {
  text-align: right;
  min-width: 100px;

  .pnl-value {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .pnl-percent {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    font-weight: 500;
  }
}

.positions-summary {
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.2);

  .summary-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-2);

    &:last-child {
      margin-bottom: 0;
    }

    span:first-child {
      font-size: var(--text-sm);
      color: var(--text-secondary);
    }

    .summary-value {
      font-family: var(--font-mono);
      font-size: var(--text-sm);
      font-weight: 600;
    }
  }
}

// 底部网格
.bottom-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-5);
}

// 订单簿区块
.orderbook-section {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.stock-tag {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  margin-left: var(--space-2);
}

.current-price-display {
  display: flex;
  align-items: center;
  gap: var(--space-3);

  .price-label {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .price-value {
    font-family: var(--font-mono);
    font-size: var(--text-lg);
    font-weight: 700;
  }

  .price-change {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--accent-green);
    padding: 2px 6px;
    background: rgba(0, 208, 132, 0.1);
    border-radius: var(--radius-sm);
  }
}

.orderbook {
  padding: var(--space-4);
}

.book-header {
  display: grid;
  grid-template-columns: 60px 1fr 1fr;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);

  span {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    text-transform: uppercase;
  }
}

.book-side {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.book-level {
  display: grid;
  grid-template-columns: 60px 1fr 1fr;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }
}

.level-side {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.level-price {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
}

.level-bar {
  position: relative;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: flex-end;

  .bar-fill {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    background: rgba(255, 71, 87, 0.2);
    border-radius: 2px;
    transition: width var(--transition-base);

    &.buy {
      background: rgba(0, 208, 132, 0.2);
    }
  }

  .bar-value {
    position: relative;
    z-index: 1;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-secondary);
  }
}

.book-spread {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-3);
  margin: var(--space-2) 0;
  border-top: 1px solid var(--border-primary);
  border-bottom: 1px solid var(--border-primary);

  .spread-label {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .spread-value {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--accent-gold);
    font-weight: 600;
  }
}

// AI推荐区块
.ai-section {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.ai-badge {
  padding: 2px 8px;
  background: linear-gradient(135deg, var(--accent-purple), var(--accent-cyan));
  color: white;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.recommendations-list {
  padding: var(--space-3);
}

.rec-item {
  display: grid;
  grid-template-columns: 50px 1fr auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }

  &:not(:last-child) {
    border-bottom: 1px solid var(--border-primary);
  }
}

.rec-rank {
  text-align: center;

  .rank-number {
    font-family: var(--font-mono);
    font-size: var(--text-xl);
    font-weight: 700;

    &.rank-excellent {
      color: var(--accent-gold);
      text-shadow: 0 0 10px var(--accent-gold-glow);
    }

    &.rank-good {
      color: var(--accent-green);
    }

    &.rank-normal {
      color: var(--accent-cyan);
    }
  }

  .rank-label {
    font-size: 10px;
    color: var(--text-muted);
  }
}

.rec-info {
  .rec-name {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 2px;
  }

  .rec-symbol {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-bottom: var(--space-2);
  }

  .rec-tags {
    display: flex;
    gap: var(--space-2);
  }

  .rec-tag {
    padding: 1px 6px;
    background: var(--bg-hover);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    font-size: 10px;
    color: var(--text-tertiary);
  }
}

.rec-reason {
  .reason-label {
    padding: var(--space-2) var(--space-3);
    background: rgba(212, 175, 55, 0.1);
    border: 1px solid rgba(212, 175, 55, 0.2);
    border-radius: var(--radius-md);
    font-size: var(--text-xs);
    color: var(--accent-gold);
    font-weight: 500;
  }
}

// 响应式
@media (max-width: 1600px) {
  .metrics-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1200px) {
  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .main-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .chart-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .metrics-row {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    gap: var(--space-4);
  }

  .chart-stats {
    grid-template-columns: 1fr;
  }

  .position-item {
    grid-template-columns: 1fr auto;

    .position-pnl {
      grid-column: 1 / -1;
      display: flex;
      justify-content: space-between;
      padding-top: var(--space-2);
      border-top: 1px solid var(--border-primary);
    }
  }
}
</style>
