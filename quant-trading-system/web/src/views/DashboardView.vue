<template>
  <div class="dashboard-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-glow"></div>
      <div class="header-content">
        <div class="header-title">
          <span class="title-icon">◈</span>
          <h1>系统概览</h1>
          <span class="header-badge">L3</span>
        </div>
        <div class="header-actions">
          <button class="cyber-btn" @click="refreshData">
            <span class="btn-icon">↻</span>
            <span class="btn-text">刷新数据</span>
          </button>
          <button class="cyber-btn primary" @click="createStrategy">
            <span class="btn-icon">+</span>
            <span class="btn-text">新建策略</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <div class="metrics-section">
      <div
        v-for="(metric, index) in metrics"
        :key="metric.label"
        class="metric-card"
        :class="{ 'card-large': metric.large, 'positive': metric.positive, 'negative': metric.negative }"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <div class="card-glow"></div>
        <div class="card-border"></div>

        <div class="metric-header">
          <span class="metric-label">{{ metric.label }}</span>
          <span class="metric-code">{{ metric.code }}</span>
        </div>

        <div class="metric-value">
          <span class="value-main data-value">{{ metric.value }}</span>
          <span v-if="metric.trend" class="value-trend" :class="getTrendClass(metric.trend)">
            {{ metric.trend }}
          </span>
        </div>

        <div class="metric-footer">
          <span class="metric-sub">{{ metric.subtext }}</span>
          <div class="metric-bar">
            <div class="metric-bar-fill" :style="{ width: `${metric.fill || 0}%` }"></div>
          </div>
        </div>

        <!-- 角落装饰 -->
        <div class="corner tl"></div>
        <div class="corner tr"></div>
        <div class="corner bl"></div>
        <div class="corner br"></div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-main">
      <!-- 左侧：资产走势 -->
      <div class="main-panel chart-section">
        <div class="panel-header">
          <div class="header-left">
            <span class="panel-icon">◫</span>
            <h3 class="panel-title">资产净值走势</h3>
            <span class="live-indicator">
              <span class="live-dot"></span>
              LIVE
            </span>
          </div>
          <div class="time-range">
            <button
              v-for="range in timeRanges"
              :key="range"
              class="range-btn"
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
        <div class="panel-footer">
          <div class="stat-row">
            <div class="stat-item">
              <span class="stat-label">初始资金</span>
              <span class="stat-value">¥1,000,000</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">当前净值</span>
              <span class="stat-value positive">¥1,245,890</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">总收益率</span>
              <span class="stat-value positive">+24.59%</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">阿尔法</span>
              <span class="stat-value">0.184</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：实时信号 -->
      <div class="side-panel signals-section">
        <div class="panel-header">
          <span class="panel-icon">⚡</span>
          <h3 class="panel-title">实时信号</h3>
          <span class="panel-badge">{{ signals.length }}</span>
        </div>
        <div class="panel-content">
          <div
            v-for="signal in signals"
            :key="signal.id"
            class="signal-item"
            :class="signal.type"
          >
            <div class="signal-icon">{{ signal.type === 'buy' ? '▲' : signal.type === 'sell' ? '▼' : '◆' }}</div>
            <div class="signal-info">
              <span class="signal-symbol">{{ signal.symbol }}</span>
              <span class="signal-strategy">{{ signal.strategy }}</span>
            </div>
            <div class="signal-price">
              <span class="price-value">{{ signal.price }}</span>
              <span class="price-time">{{ signal.time }}</span>
            </div>
            <div class="signal-glow" :class="signal.type"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：持仓与策略 -->
    <div class="dashboard-bottom">
      <!-- 持仓列表 -->
      <div class="bottom-panel positions-panel">
        <div class="panel-header">
          <span class="panel-icon">◐</span>
          <h3 class="panel-title">当前持仓</h3>
        </div>
        <div class="panel-content">
          <table class="cyber-table">
            <thead>
              <tr>
                <th>标的</th>
                <th>方向</th>
                <th>数量</th>
                <th>成本价</th>
                <th>现价</th>
                <th>盈亏</th>
                <th>占比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pos in positions" :key="pos.symbol">
                <td>
                  <span class="cell-symbol">{{ pos.symbol }}</span>
                  <span class="cell-name">{{ pos.name }}</span>
                </td>
                <td>
                  <span class="cyber-tag" :class="pos.side">{{ pos.side === 'long' ? '多' : '空' }}</span>
                </td>
                <td class="data-value">{{ pos.quantity }}</td>
                <td class="data-value">{{ pos.costPrice }}</td>
                <td class="data-value">{{ pos.currentPrice }}</td>
                <td :class="pos.pnl >= 0 ? 'positive' : 'negative'" class="data-value">
                  {{ pos.pnl >= 0 ? '+' : '' }}{{ pos.pnl }}%
                </td>
                <td>
                  <div class="cell-bar">
                    <div class="cell-bar-fill" :style="{ width: `${pos.weight}%` }"></div>
                    <span>{{ pos.weight }}%</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 策略状态 -->
      <div class="bottom-panel strategies-panel">
        <div class="panel-header">
          <span class="panel-icon">◈</span>
          <h3 class="panel-title">策略状态</h3>
        </div>
        <div class="panel-content">
          <div v-for="strategy in strategies" :key="strategy.id" class="strategy-item">
            <div class="strategy-info">
              <span class="strategy-name">{{ strategy.name }}</span>
              <span class="strategy-type">{{ strategy.type }}</span>
            </div>
            <div class="strategy-metrics">
              <div class="metric">
                <span class="metric-label">收益</span>
                <span :class="strategy.return >= 0 ? 'positive' : 'negative'" class="metric-value">
                  {{ strategy.return }}%
                </span>
              </div>
              <div class="metric">
                <span class="metric-label">夏普</span>
                <span class="metric-value">{{ strategy.sharpe }}</span>
              </div>
            </div>
            <div class="strategy-status">
              <span class="status-dot" :class="strategy.status"></span>
              <span class="status-text">{{ strategy.status === 'active' ? '运行中' : '已暂停' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import EquityChart from '@/components/charts/EquityChart.vue'

const selectedRange = ref('1D')
const timeRanges = ['1H', '1D', '1W', '1M', 'YTD', 'ALL']

const metrics = ref([
  {
    label: '总资产',
    code: 'AUM-001',
    value: '¥1,245,890.50',
    trend: '+5.2%',
    subtext: '较初始资金',
    large: true,
    positive: true,
    fill: 85,
  },
  {
    label: '今日盈亏',
    code: 'P/L-DAY',
    value: '+¥29,245.80',
    trend: '+2.4%',
    subtext: '日收益率',
    positive: true,
    fill: 70,
  },
  {
    label: '累计收益',
    code: 'RET-TOT',
    value: '+¥245,890.50',
    trend: '+24.6%',
    subtext: '年化收益 18.2%',
    positive: true,
    fill: 60,
  },
  {
    label: '夏普比率',
    code: 'SHARPE',
    value: '1.84',
    trend: '+0.12',
    subtext: '风险调整后收益',
    fill: 75,
  },
  {
    label: '最大回撤',
    code: 'MDD',
    value: '-8.50%',
    trend: '-0.5%',
    subtext: '历史最大',
    negative: true,
    fill: 25,
  },
  {
    label: '胜率',
    code: 'WIN-RATE',
    value: '58.4%',
    trend: '+1.2%',
    subtext: '总交易 142笔',
    fill: 58,
  },
])

const signals = ref([
  { id: 1, symbol: '600519', strategy: '双均线突破', type: 'buy', price: '1,688.00', time: '09:32:15' },
  { id: 2, symbol: '000858', strategy: '趋势跟踪', type: 'sell', price: '158.50', time: '09:31:42' },
  { id: 3, symbol: '300750', strategy: '动量策略', type: 'buy', price: '198.20', time: '09:30:08' },
  { id: 4, symbol: '601888', strategy: '均值回归', type: 'hold', price: '68.35', time: '09:28:33' },
])

const positions = ref([
  { symbol: '600519', name: '贵州茅台', side: 'long', quantity: 100, costPrice: '1,650.00', currentPrice: '1,688.00', pnl: 2.3, weight: 35 },
  { symbol: '300750', name: '宁德时代', side: 'long', quantity: 500, costPrice: '195.00', currentPrice: '198.20', pnl: 1.6, weight: 25 },
  { symbol: '000333', name: '美的集团', side: 'long', quantity: 1000, costPrice: '58.50', currentPrice: '59.20', pnl: 1.2, weight: 20 },
  { symbol: '601318', name: '中国平安', side: 'short', quantity: 800, costPrice: '45.00', currentPrice: '44.20', pnl: 1.8, weight: 20 },
])

const strategies = ref([
  { id: 's1', name: '双均线突破', type: '趋势跟踪', return: 24.5, sharpe: 1.92, status: 'active' },
  { id: 's2', name: '均值回归', type: '统计套利', return: 18.3, sharpe: 1.65, status: 'active' },
  { id: 's3', name: '动量策略', type: '趋势跟踪', return: 15.2, sharpe: 1.45, status: 'paused' },
])

function getTrendClass(trend: string) {
  if (trend.startsWith('+')) return 'trend-up'
  if (trend.startsWith('-')) return 'trend-down'
  return 'trend-neutral'
}

function refreshData() {
  // 刷新数据逻辑
}

function createStrategy() {
  // 创建策略逻辑
}

onMounted(() => {
  // 页面加载动画
})
</script>

<style scoped>
.dashboard-page {
  animation: fade-in-up 0.6s ease;
}

/* 页面头部 */
.page-header {
  position: relative;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-subtle);
}

.header-glow {
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 200px;
  height: 1px;
  background: linear-gradient(90deg, var(--neon-cyan), transparent);
  box-shadow: 0 0 20px var(--neon-cyan);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  font-size: 1.5rem;
  color: var(--neon-cyan);
  text-shadow: 0 0 20px var(--neon-cyan);
}

.header-title h1 {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

.header-badge {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  padding: 0.25rem 0.75rem;
  background: var(--neon-cyan-dim);
  border: 1px solid var(--neon-cyan);
  color: var(--neon-cyan);
  letter-spacing: 0.1em;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

/* 指标卡片 */
.metrics-section {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.metric-card {
  position: relative;
  background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%);
  border: 1px solid var(--border-subtle);
  padding: 1.25rem;
  overflow: hidden;
  animation: fade-in-up 0.6s ease backwards;
}

.metric-card:hover {
  border-color: var(--border-medium);
}

.metric-card.positive:hover {
  border-color: rgba(0, 240, 255, 0.3);
  box-shadow: 0 0 30px rgba(0, 240, 255, 0.1);
}

.metric-card.negative:hover {
  border-color: rgba(255, 0, 170, 0.3);
  box-shadow: 0 0 30px rgba(255, 0, 170, 0.1);
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
  opacity: 0.3;
}

.metric-card.positive .card-glow {
  background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
}

.metric-card.negative .card-glow {
  background: linear-gradient(90deg, transparent, var(--neon-magenta), transparent);
}

.corner {
  position: absolute;
  width: 6px;
  height: 6px;
  border-color: var(--border-medium);
}

.corner.tl { top: 0; left: 0; border-top: 1px solid; border-left: 1px solid; }
.corner.tr { top: 0; right: 0; border-top: 1px solid; border-right: 1px solid; }
.corner.bl { bottom: 0; left: 0; border-bottom: 1px solid; border-left: 1px solid; }
.corner.br { bottom: 0; right: 0; border-bottom: 1px solid; border-right: 1px solid; }

.metric-card.positive .corner { border-color: rgba(0, 240, 255, 0.3); }
.metric-card.negative .corner { border-color: rgba(255, 0, 170, 0.3); }

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.metric-code {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.value-main {
  font-family: var(--font-mono);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.value-trend {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
}

.value-trend.trend-up {
  color: var(--signal-buy);
}

.value-trend.trend-down {
  color: var(--signal-sell);
}

.metric-footer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metric-sub {
  font-size: 0.625rem;
  color: var(--text-tertiary);
}

.metric-bar {
  height: 2px;
  background: var(--bg-elevated);
  overflow: hidden;
}

.metric-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-amber));
  transition: width 0.6s ease;
}

.metric-card.positive .metric-bar-fill {
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
}

.metric-card.negative .metric-bar-fill {
  background: linear-gradient(90deg, var(--neon-magenta), var(--neon-amber));
}

/* 主内容区 */
.dashboard-main {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.main-panel, .side-panel {
  background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%);
  border: 1px solid var(--border-subtle);
  position: relative;
}

.main-panel::before, .side-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--neon-cyan), transparent);
  opacity: 0.5;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.panel-icon {
  font-size: 1rem;
  color: var(--neon-cyan);
}

.panel-title {
  font-family: var(--font-display);
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: var(--neon-magenta);
  margin-left: 0.5rem;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: var(--neon-magenta);
  border-radius: 50%;
  animation: blink 1s ease-in-out infinite;
}

.time-range {
  display: flex;
  gap: 0.25rem;
}

.range-btn {
  padding: 0.375rem 0.75rem;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.range-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-medium);
}

.range-btn.active {
  background: var(--neon-cyan-dim);
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.panel-content {
  padding: 1.5rem;
  min-height: 300px;
}

.panel-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.stat-row {
  display: flex;
  justify-content: space-around;
  gap: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-value.positive {
  color: var(--signal-buy);
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

/* 信号列表 */
.signals-section .panel-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
}

.signal-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.signal-item:hover {
  border-color: var(--border-medium);
}

.signal-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.625rem;
  border-radius: 50%;
}

.signal-item.buy .signal-icon {
  background: rgba(0, 240, 255, 0.1);
  color: var(--signal-buy);
}

.signal-item.sell .signal-icon {
  background: rgba(255, 0, 170, 0.1);
  color: var(--signal-sell);
}

.signal-item.hold .signal-icon {
  background: rgba(255, 184, 0, 0.1);
  color: var(--signal-hold);
}

.signal-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  flex: 1;
}

.signal-symbol {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.signal-strategy {
  font-size: 0.625rem;
  color: var(--text-tertiary);
}

.signal-price {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.price-value {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--neon-amber);
}

.price-time {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-muted);
}

.signal-glow {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.signal-item:hover .signal-glow {
  opacity: 1;
}

.signal-glow.buy { background: var(--signal-buy); box-shadow: 0 0 10px var(--signal-buy); }
.signal-glow.sell { background: var(--signal-sell); box-shadow: 0 0 10px var(--signal-sell); }
.signal-glow.hold { background: var(--signal-hold); box-shadow: 0 0 10px var(--signal-hold); }

.panel-badge {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  padding: 0.25rem 0.5rem;
  background: var(--neon-cyan-dim);
  border: 1px solid var(--neon-cyan);
  color: var(--neon-cyan);
}

/* 底部区域 */
.dashboard-bottom {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

.bottom-panel {
  background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%);
  border: 1px solid var(--border-subtle);
  position: relative;
}

.bottom-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--neon-cyan), transparent);
  opacity: 0.5;
}

/* 表格 */
.cyber-table {
  width: 100%;
  border-collapse: collapse;
}

.cyber-table th {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-tertiary);
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.cyber-table td {
  padding: 0.875rem 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.cyber-table tbody tr:hover {
  background: var(--bg-surface);
}

.cell-symbol {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
  margin-right: 0.5rem;
}

.cell-name {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.cyber-tag {
  display: inline-flex;
  padding: 0.25rem 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 600;
}

.cyber-tag.long {
  background: rgba(0, 240, 255, 0.1);
  color: var(--signal-buy);
  border: 1px solid rgba(0, 240, 255, 0.3);
}

.cyber-tag.short {
  background: rgba(255, 0, 170, 0.1);
  color: var(--signal-sell);
  border: 1px solid rgba(255, 0, 170, 0.3);
}

.cell-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.625rem;
}

.cell-bar-fill {
  height: 4px;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
  min-width: 20px;
}

/* 策略列表 */
.strategies-panel .panel-content {
  padding: 1rem;
}

.strategy-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--border-subtle);
}

.strategy-item:last-child {
  border-bottom: none;
}

.strategy-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.strategy-name {
  font-weight: 600;
  color: var(--text-primary);
}

.strategy-type {
  font-size: 0.625rem;
  color: var(--text-tertiary);
}

.strategy-metrics {
  display: flex;
  gap: 1.5rem;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.metric-label {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-tertiary);
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.metric-value.positive {
  color: var(--signal-buy);
}

.metric-value.negative {
  color: var(--signal-sell);
}

.strategy-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.active {
  background: var(--neon-cyan);
  box-shadow: 0 0 10px var(--neon-cyan);
  animation: blink 2s ease-in-out infinite;
}

.status-dot.paused {
  background: var(--text-muted);
}

.status-text {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-tertiary);
}

/* 响应式 */
@media (max-width: 1400px) {
  .metrics-section {
    grid-template-columns: repeat(3, 1fr);
  }

  .dashboard-main,
  .dashboard-bottom {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .metrics-section {
    grid-template-columns: repeat(2, 1fr);
  }

  .header-content {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .time-range {
    display: none;
  }
}
</style>
