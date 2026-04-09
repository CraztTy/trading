<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">实盘监控</h1>
      <div class="page-actions">
        <div class="status-indicator" :class="{ active: isConnected }">
          <span class="status-dot"></span>
          {{ isConnected ? '已连接' : '未连接' }}
        </div>
        <button class="btn btn-primary" @click="toggleTrading" :class="{ danger: isTrading }">
          <span class="btn-icon">{{ isTrading ? '⏹' : '▶' }}</span>
          {{ isTrading ? '停止交易' : '启动交易' }}
        </button>
      </div>
    </div>

    <div class="live-grid">
      <!-- 左侧：实时行情与信号 -->
      <div class="live-left">
        <!-- 组合概览 -->
        <div class="metrics-summary">
          <div class="summary-card large">
            <span class="summary-label">总资产</span>
            <span class="summary-value">¥{{ portfolio.totalValue.toLocaleString() }}</span>
            <span class="summary-change" :class="{ positive: portfolio.dailyPnl > 0, negative: portfolio.dailyPnl < 0 }">
              {{ portfolio.dailyPnl > 0 ? '+' : '' }}¥{{ portfolio.dailyPnl.toLocaleString() }}
            </span>
          </div>
          <div class="summary-card">
            <span class="summary-label">可用资金</span>
            <span class="summary-value">¥{{ portfolio.cash.toLocaleString() }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">持仓市值</span>
            <span class="summary-value">¥{{ portfolio.positionValue.toLocaleString() }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">今日收益率</span>
            <span class="summary-value" :class="{ positive: portfolio.dailyReturn > 0, negative: portfolio.dailyReturn < 0 }">
              {{ portfolio.dailyReturn > 0 ? '+' : '' }}{{ portfolio.dailyReturn }}%
            </span>
          </div>
        </div>

        <!-- 实时信号流 -->
        <div class="panel signals-panel">
          <div class="panel-header">
            <h3 class="panel-title">实时信号</h3>
            <span class="panel-badge live">LIVE</span>
          </div>
          <div class="panel-content">
            <div class="signals-list" ref="signalsList">
              <div
                v-for="signal in signals"
                :key="signal.id"
                class="signal-item"
                :class="[signal.type, { new: signal.isNew }]"
              >
                <div class="signal-icon">{{ getSignalIcon(signal.type) }}</div>
                <div class="signal-info">
                  <div class="signal-header">
                    <span class="signal-symbol">{{ signal.symbol }}</span>
                    <span class="signal-name">{{ signal.name }}</span>
                  </div>
                  <div class="signal-details">
                    <span class="signal-strategy">{{ signal.strategy }}</span>
                    <span class="signal-price">¥{{ signal.price.toFixed(2) }}</span>
                  </div>
                </div>
                <span class="signal-time">{{ signal.time }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 风控状态 -->
        <div class="panel risk-panel">
          <div class="panel-header">
            <h3 class="panel-title">风控监控</h3>
            <span class="panel-badge" :class="riskStatus.class">{{ riskStatus.text }}</span>
          </div>
          <div class="panel-content">
            <div class="risk-metrics">
              <div
                v-for="metric in riskMetrics"
                :key="metric.name"
                class="risk-metric"
              >
                <div class="risk-header">
                  <span class="risk-name">{{ metric.name }}</span>
                  <span class="risk-value" :class="metric.status">{{ metric.value }}</span>
                </div>
                <div class="risk-bar">
                  <div class="risk-fill" :style="{ width: metric.percent + '%' }" :class="metric.status"></div>
                </div>
                <span class="risk-limit">限制: {{ metric.limit }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：持仓与交易 -->
      <div class="live-right">
        <!-- 持仓列表 -->
        <div class="panel positions-panel">
          <div class="panel-header">
            <h3 class="panel-title">当前持仓</h3>
            <span class="panel-badge">{{ positions.length }} 只股票</span>
          </div>
          <div class="panel-content">
            <div class="positions-list">
              <div
                v-for="position in positions"
                :key="position.symbol"
                class="position-item"
              >
                <div class="position-header">
                  <div class="position-info">
                    <span class="position-symbol">{{ position.symbol }}</span>
                    <span class="position-name">{{ position.name }}</span>
                  </div>
                  <div class="position-pnl" :class="{ positive: position.pnl > 0, negative: position.pnl < 0 }">
                    {{ position.pnl > 0 ? '+' : '' }}{{ position.pnl }}%
                  </div>
                </div>
                <div class="position-details">
                  <div class="detail">
                    <span class="detail-label">持仓</span>
                    <span class="detail-value">{{ position.qty }}股</span>
                  </div>
                  <div class="detail">
                    <span class="detail-label">成本</span>
                    <span class="detail-value">¥{{ position.cost.toFixed(2) }}</span>
                  </div>
                  <div class="detail">
                    <span class="detail-label">现价</span>
                    <span class="detail-value">¥{{ position.price.toFixed(2) }}</span>
                  </div>
                  <div class="detail">
                    <span class="detail-label">市值</span>
                    <span class="detail-value">¥{{ (position.qty * position.price).toLocaleString() }}</span>
                  </div>
                </div>
                <div class="position-alerts" v-if="position.alerts?.length">
                  <span
                    v-for="alert in position.alerts"
                    :key="alert"
                    class="alert-tag"
                    :class="alert.type"
                  >
                    {{ alert.message }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 最近交易 -->
        <div class="panel trades-panel">
          <div class="panel-header">
            <h3 class="panel-title">最近成交</h3>
            <button class="btn-text" @click="showAllTrades = true">查看全部</button>
          </div>
          <div class="panel-content">
            <div class="trades-list">
              <div
                v-for="trade in recentTrades"
                :key="trade.id"
                class="trade-item"
              >
                <div class="trade-icon" :class="trade.direction">
                  {{ trade.direction === 'buy' ? '▲' : '▼' }}
                </div>
                <div class="trade-info">
                  <span class="trade-symbol">{{ trade.symbol }}</span>
                  <span class="trade-qty">{{ trade.qty }}股 @ ¥{{ trade.price.toFixed(2) }}</span>
                </div>
                <span class="trade-time">{{ trade.time }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统日志 -->
        <div class="panel logs-panel">
          <div class="panel-header">
            <h3 class="panel-title">系统日志</h3>
            <div class="log-levels">
              <button
                v-for="level in logLevels"
                :key="level"
                class="log-filter"
                :class="{ active: selectedLogLevel === level }"
                @click="selectedLogLevel = level"
              >
                {{ level }}
              </button>
            </div>
          </div>
          <div class="panel-content">
            <div class="logs-list" ref="logsList">
              <div
                v-for="log in filteredLogs"
                :key="log.id"
                class="log-item"
                :class="log.level"
              >
                <span class="log-time">{{ log.time }}</span>
                <span class="log-level-badge">{{ log.level }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 全部交易弹窗 -->
    <div class="modal" v-if="showAllTrades" @click.self="showAllTrades = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>今日全部成交</h3>
          <button class="btn-icon-only" @click="showAllTrades = false">✕</button>
        </div>
        <div class="modal-body">
          <table class="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>代码</th>
                <th>方向</th>
                <th>价格</th>
                <th>数量</th>
                <th>金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trade in allTrades" :key="trade.id">
                <td>{{ trade.time }}</td>
                <td>{{ trade.symbol }}</td>
                <td>
                  <span class="direction-badge" :class="trade.direction">
                    {{ trade.direction === 'buy' ? '买入' : '卖出' }}
                  </span>
                </td>
                <td>¥{{ trade.price.toFixed(2) }}</td>
                <td>{{ trade.qty }}</td>
                <td>¥{{ (trade.price * trade.qty).toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const isConnected = ref(true)
const isTrading = ref(false)
const showAllTrades = ref(false)
const selectedLogLevel = ref('ALL')
const signalsList = ref<HTMLElement>()
const logsList = ref<HTMLElement>()

const portfolio = ref({
  totalValue: 1245890.50,
  cash: 456890.30,
  positionValue: 789000.20,
  dailyPnl: 29245.80,
  dailyReturn: 2.35
})

const signals = ref([
  { id: 1, type: 'buy', symbol: '600519.SH', name: '贵州茅台', strategy: '双均线突破', price: 1685.00, time: '09:45:23', isNew: true },
  { id: 2, type: 'sell', symbol: '300750.SZ', name: '宁德时代', strategy: '止盈策略', price: 215.50, time: '09:42:15', isNew: false },
  { id: 3, type: 'risk', symbol: '000858.SZ', name: '五粮液', strategy: '风控提醒', price: 142.30, time: '09:40:08', isNew: false },
  { id: 4, type: 'buy', symbol: '000333.SZ', name: '美的集团', strategy: 'MACD金叉', price: 65.80, time: '09:38:42', isNew: false },
  { id: 5, type: 'stop', symbol: '002594.SZ', name: '比亚迪', strategy: '止损触发', price: 245.00, time: '09:35:18', isNew: false }
])

const positions = ref([
  {
    symbol: '600519.SH',
    name: '贵州茅台',
    qty: 100,
    cost: 1650.00,
    price: 1685.00,
    pnl: 2.12,
    alerts: [{ type: 'warning', message: '接近止盈位' }]
  },
  {
    symbol: '000858.SZ',
    name: '五粮液',
    qty: 200,
    cost: 145.00,
    price: 142.30,
    pnl: -1.86,
    alerts: [{ type: 'danger', message: '触及止损线' }]
  },
  {
    symbol: '000333.SZ',
    name: '美的集团',
    qty: 500,
    cost: 64.50,
    price: 65.80,
    pnl: 2.02,
    alerts: []
  }
])

const recentTrades = ref([
  { id: 1, symbol: '600519.SH', direction: 'buy', price: 1685.00, qty: 100, time: '09:45:23' },
  { id: 2, symbol: '300750.SZ', direction: 'sell', price: 215.50, qty: 150, time: '09:42:15' },
  { id: 3, symbol: '000333.SZ', direction: 'buy', price: 65.80, qty: 500, time: '09:38:42' }
])

const allTrades = ref([
  ...recentTrades.value,
  { id: 4, symbol: '002594.SZ', direction: 'sell', price: 245.00, qty: 80, time: '09:35:18' },
  { id: 5, symbol: '300750.SZ', direction: 'buy', price: 198.00, qty: 150, time: '09:32:05' }
])

const riskMetrics = ref([
  { name: '单票仓位', value: '12.5%', limit: '20%', percent: 62.5, status: 'normal' },
  { name: '总仓位', value: '45.2%', limit: '60%', percent: 75.3, status: 'warning' },
  { name: '日亏损', value: '0.8%', limit: '2%', percent: 40, status: 'normal' },
  { name: '连续亏损', value: '1次', limit: '3次', percent: 33.3, status: 'normal' }
])

const logLevels = ['ALL', 'INFO', 'WARN', 'ERROR']

const logs = ref([
  { id: 1, time: '09:45:23', level: 'INFO', message: '买入信号触发: 600519.SH @ 1685.00' },
  { id: 2, time: '09:45:22', level: 'INFO', message: '订单已成交: 600519.SH 100股' },
  { id: 3, time: '09:42:15', level: 'WARN', message: '卖出信号触发: 300750.SZ @ 215.50' },
  { id: 4, time: '09:42:14', level: 'INFO', message: '订单已成交: 300750.SZ 150股' },
  { id: 5, time: '09:40:08', level: 'ERROR', message: '风控拦截: 000858.SZ 日亏损接近限制' },
  { id: 6, time: '09:38:42', level: 'INFO', message: '买入信号触发: 000333.SZ @ 65.80' },
  { id: 7, time: '09:38:41', level: 'INFO', message: '订单已成交: 000333.SZ 500股' }
])

const riskStatus = computed(() => {
  const hasWarning = riskMetrics.value.some(m => m.status === 'warning')
  const hasDanger = riskMetrics.value.some(m => m.status === 'danger')
  if (hasDanger) return { text: '告警', class: 'danger' }
  if (hasWarning) return { text: '注意', class: 'warning' }
  return { text: '正常', class: 'success' }
})

const filteredLogs = computed(() => {
  if (selectedLogLevel.value === 'ALL') return logs.value
  return logs.value.filter(l => l.level === selectedLogLevel.value)
})

function getSignalIcon(type: string) {
  const icons: Record<string, string> = {
    buy: '▲',
    sell: '▼',
    risk: '⚠',
    stop: '⏹'
  }
  return icons[type] || '●'
}

function toggleTrading() {
  isTrading.value = !isTrading.value
}

// 模拟实时数据更新
let interval: number

onMounted(() => {
  interval = window.setInterval(() => {
    // 模拟价格波动
    positions.value.forEach(p => {
      const change = (Math.random() - 0.5) * 0.5
      p.price = Math.max(0.01, p.price * (1 + change / 100))
      p.pnl = ((p.price - p.cost) / p.cost) * 100
    })

    // 更新组合市值
    portfolio.value.positionValue = positions.value.reduce((sum, p) => sum + p.qty * p.price, 0)
    portfolio.value.totalValue = portfolio.value.cash + portfolio.value.positionValue
  }, 3000)
})

onUnmounted(() => {
  clearInterval(interval)
})
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
  align-items: center;
  gap: 1rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: var(--bg-tertiary);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.status-indicator.active {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator.active .status-dot {
  background: var(--accent-success);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
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
  background: var(--accent-success);
  color: var(--bg-primary);
}

.btn-primary:hover {
  background: #34d399;
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
}

.btn-primary.danger {
  background: var(--accent-danger);
}

.btn-primary.danger:hover {
  background: #f87171;
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
}

.btn-text {
  background: transparent;
  border: none;
  color: var(--accent-secondary);
  font-size: 0.8125rem;
  cursor: pointer;
}

.btn-text:hover {
  color: var(--accent-primary);
}

.btn-icon-only {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.live-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 1.5rem;
}

.metrics-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
}

.summary-card.large {
  grid-column: span 2;
  padding: 1.25rem;
}

.summary-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.summary-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.summary-card.large .summary-value {
  font-size: 1.5rem;
}

.summary-change {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
}

.summary-change.positive {
  color: var(--accent-success);
}

.summary-change.negative {
  color: var(--accent-danger);
}

.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.panel:last-child {
  margin-bottom: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
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

.panel-badge.live {
  background: var(--accent-danger);
  color: white;
  animation: pulse 2s infinite;
}

.panel-badge.success {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.panel-badge.warning {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.panel-badge.danger {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.panel-content {
  padding: 1rem;
}

.signals-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 280px;
  overflow-y: auto;
}

.signal-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
  border-left: 3px solid transparent;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.signal-item.new {
  background: rgba(245, 158, 11, 0.1);
}

.signal-item.buy {
  border-left-color: var(--accent-success);
}

.signal-item.sell {
  border-left-color: var(--accent-danger);
}

.signal-item.risk {
  border-left-color: var(--accent-warning);
}

.signal-item.stop {
  border-left-color: var(--accent-secondary);
}

.signal-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.signal-item.buy .signal-icon {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.signal-item.sell .signal-icon {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.signal-item.risk .signal-icon {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.signal-item.stop .signal-icon {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-secondary);
}

.signal-info {
  flex: 1;
  min-width: 0;
}

.signal-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.125rem;
}

.signal-symbol {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.signal-name {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.signal-details {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.signal-strategy {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.signal-price {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--accent-primary);
}

.signal-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6875rem;
  color: var(--text-muted);
}

.risk-metrics {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.risk-metric {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.risk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-name {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.risk-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 500;
}

.risk-value.normal {
  color: var(--accent-success);
}

.risk-value.warning {
  color: var(--accent-warning);
}

.risk-value.danger {
  color: var(--accent-danger);
}

.risk-bar {
  height: 4px;
  background: var(--bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}

.risk-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.risk-fill.normal {
  background: var(--accent-success);
}

.risk-fill.warning {
  background: var(--accent-warning);
}

.risk-fill.danger {
  background: var(--accent-danger);
}

.risk-limit {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.positions-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 300px;
  overflow-y: auto;
}

.position-item {
  padding: 0.875rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
  border: 1px solid var(--border-primary);
}

.position-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.position-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.position-symbol {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.position-name {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.position-pnl {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

.position-pnl.positive {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.position-pnl.negative {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.position-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.detail-label {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.detail-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.position-alerts {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-primary);
}

.alert-tag {
  font-size: 0.6875rem;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
}

.alert-tag.warning {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.alert-tag.danger {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.trades-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.trade-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem;
  background: var(--bg-primary);
  border-radius: 0.375rem;
}

.trade-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.trade-icon.buy {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.trade-icon.sell {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.trade-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.trade-symbol {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  color: var(--text-primary);
}

.trade-qty {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.trade-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6875rem;
  color: var(--text-muted);
}

.log-levels {
  display: flex;
  gap: 0.25rem;
}

.log-filter {
  padding: 0.25rem 0.5rem;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.6875rem;
  cursor: pointer;
}

.log-filter.active {
  background: var(--accent-primary);
  color: var(--bg-primary);
  border-color: var(--accent-primary);
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  max-height: 200px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
}

.log-item {
  display: flex;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 0.25rem;
}

.log-item:hover {
  background: var(--bg-hover);
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-level-badge {
  padding: 0 0.375rem;
  border-radius: 0.125rem;
  font-size: 0.625rem;
  font-weight: 500;
  text-transform: uppercase;
}

.log-item.INFO .log-level-badge {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-secondary);
}

.log-item.WARN .log-level-badge {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.log-item.ERROR .log-level-badge {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.log-message {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.modal-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-body {
  padding: 1.25rem;
  max-height: 60vh;
  overflow-y: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 0.75rem;
  text-align: left;
  font-size: 0.8125rem;
}

.data-table th {
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.data-table td {
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-primary);
}

.direction-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.direction-badge.buy {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.direction-badge.sell {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.positive {
  color: var(--accent-success);
}

.negative {
  color: var(--accent-danger);
}

@media (max-width: 1200px) {
  .live-grid {
    grid-template-columns: 1fr;
  }

  .metrics-summary {
    grid-template-columns: repeat(4, 1fr);
  }

  .summary-card.large {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .metrics-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
