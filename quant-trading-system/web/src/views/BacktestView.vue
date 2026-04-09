<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">回测中心</h1>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="showHistory = !showHistory">
          <span class="btn-icon">📋</span>
          {{ showHistory ? '隐藏历史' : '历史记录' }}
        </button>
        <button class="btn btn-primary" @click="startBacktest" :disabled="isRunning">
          <span class="btn-icon">▶</span>
          {{ isRunning ? '运行中...' : '开始回测' }}
        </button>
      </div>
    </div>

    <div class="backtest-layout">
      <!-- 配置面板 -->
      <div class="config-panel">
        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">回测配置</h3>
          </div>
          <div class="panel-content">
            <div class="form-group">
              <label class="form-label">股票代码</label>
              <input
                v-model="config.symbols"
                type="text"
                class="form-input"
                placeholder="例如: 600519.SH, 000858.SZ"
              />
              <span class="form-hint">多个代码用逗号分隔</span>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">开始日期</label>
                <input v-model="config.startDate" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">结束日期</label>
                <input v-model="config.endDate" type="date" class="form-input" />
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">初始资金</label>
              <div class="input-with-prefix">
                <span class="input-prefix">¥</span>
                <input
                  v-model.number="config.initialCapital"
                  type="number"
                  class="form-input"
                  min="100000"
                  step="100000"
                />
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">选择策略</label>
              <div class="strategy-list">
                <label
                  v-for="strategy in strategies"
                  :key="strategy.id"
                  class="strategy-checkbox"
                  :class="{ selected: config.selectedStrategies.includes(strategy.id) }"
                >
                  <input
                    type="checkbox"
                    :value="strategy.id"
                    v-model="config.selectedStrategies"
                  />
                  <span class="strategy-name">{{ strategy.name }}</span>
                  <span class="strategy-desc">{{ strategy.desc }}</span>
                </label>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">回测周期</label>
              <select v-model="config.period" class="form-select">
                <option value="1d">日线</option>
                <option value="1h">小时线</option>
                <option value="15m">15分钟线</option>
                <option value="5m">5分钟线</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 风控参数 -->
        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">风控参数</h3>
          </div>
          <div class="panel-content">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">单票仓位上限</label>
                <div class="input-with-suffix">
                  <input
                    v-model.number="config.maxPositionPerStock"
                    type="number"
                    class="form-input"
                    min="0.01"
                    max="1"
                    step="0.01"
                  />
                  <span class="input-suffix">%</span>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">总仓位上限</label>
                <div class="input-with-suffix">
                  <input
                    v-model.number="config.maxTotalPosition"
                    type="number"
                    class="form-input"
                    min="0.01"
                    max="1"
                    step="0.01"
                  />
                  <span class="input-suffix">%</span>
                </div>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">止损比例</label>
                <div class="input-with-suffix">
                  <input
                    v-model.number="config.stopLoss"
                    type="number"
                    class="form-input"
                    min="0.001"
                    max="0.5"
                    step="0.001"
                  />
                  <span class="input-suffix">%</span>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">日亏损熔断</label>
                <div class="input-with-suffix">
                  <input
                    v-model.number="config.maxDailyLoss"
                    type="number"
                    class="form-input"
                    min="0.001"
                    max="0.5"
                    step="0.001"
                  />
                  <span class="input-suffix">%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 结果面板 -->
      <div class="results-panel">
        <div class="panel" v-if="!results && !isRunning">
          <div class="panel-content empty-state">
            <div class="empty-icon">📊</div>
            <h3>开始回测</h3>
            <p>配置参数后点击"开始回测"按钮</p>
          </div>
        </div>

        <div class="panel" v-else-if="isRunning">
          <div class="panel-content loading-state">
            <div class="progress-ring">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="var(--border-primary)" stroke-width="4" />
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke="var(--accent-primary)"
                  stroke-width="4"
                  stroke-dasharray="283"
                  :stroke-dashoffset="283 - (283 * progress) / 100"
                  stroke-linecap="round"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <span class="progress-text">{{ progress }}%</span>
            </div>
            <p class="loading-text">{{ loadingText }}</p>
          </div>
        </div>

        <template v-else-if="results">
          <!-- 汇总指标 -->
          <div class="metrics-summary">
            <div
              v-for="metric in summaryMetrics"
              :key="metric.label"
              class="summary-card"
              :class="{ positive: metric.positive, negative: metric.negative }"
            >
              <span class="summary-label">{{ metric.label }}</span>
              <span class="summary-value">{{ metric.value }}</span>
              <span class="summary-subtext" v-if="metric.subtext">{{ metric.subtext }}</span>
            </div>
          </div>

          <!-- 收益曲线 -->
          <div class="panel chart-panel">
            <div class="panel-header">
              <h3 class="panel-title">收益曲线</h3>
              <div class="legend">
                <span class="legend-item strategy">
                  <span class="legend-dot"></span>
                  策略收益
                </span>
                <span class="legend-item benchmark">
                  <span class="legend-dot"></span>
                  基准收益
                </span>
              </div>
            </div>
            <div class="panel-content">
              <canvas ref="chartCanvas" height="300"></canvas>
            </div>
          </div>

          <!-- 交易记录 -->
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">交易记录</h3>
              <span class="panel-badge">{{ results.trades?.length || 0 }} 笔</span>
            </div>
            <div class="panel-content">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>代码</th>
                    <th>方向</th>
                    <th>价格</th>
                    <th>数量</th>
                    <th>盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="trade in displayedTrades" :key="trade.id">
                    <td class="mono">{{ trade.time }}</td>
                    <td class="mono">{{ trade.code }}</td>
                    <td>
                      <span class="direction-badge" :class="trade.direction">
                        {{ trade.direction === 'buy' ? '买入' : '卖出' }}
                      </span>
                    </td>
                    <td class="mono">¥{{ trade.price.toFixed(2) }}</td>
                    <td class="mono">{{ trade.qty }}</td>
                    <td
                      class="mono"
                      :class="{ positive: trade.pnl > 0, negative: trade.pnl < 0 }"
                    >
                      {{ trade.pnl > 0 ? '+' : '' }}{{ trade.pnl.toFixed(2) }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div class="pagination" v-if="results.trades?.length > 10">
                <button
                  class="btn-text"
                  @click="showAllTrades = !showAllTrades"
                >
                  {{ showAllTrades ? '收起' : `查看全部 ${results.trades.length} 笔交易` }}
                </button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 历史记录侧边栏 -->
      <div class="history-sidebar" v-if="showHistory">
        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">历史记录</h3>
            <button class="btn-icon-only" @click="showHistory = false">✕</button>
          </div>
          <div class="panel-content">
            <div class="history-list">
              <div
                v-for="item in history"
                :key="item.id"
                class="history-item"
                @click="loadHistory(item)"
              >
                <div class="history-info">
                  <span class="history-date">{{ item.date }}</span>
                  <span class="history-strategies">{{ item.strategies.join(', ') }}</span>
                </div>
                <span
                  class="history-return"
                  :class="{ positive: item.return > 0, negative: item.return < 0 }"
                >
                  {{ item.return > 0 ? '+' : '' }}{{ item.return }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

const isRunning = ref(false)
const progress = ref(0)
const loadingText = ref('初始化回测...')
const results = ref<any>(null)
const showHistory = ref(false)
const showAllTrades = ref(false)
const chartCanvas = ref<HTMLCanvasElement>()

const config = ref({
  symbols: '600519.SH, 000858.SZ, 300750.SZ',
  startDate: '2024-01-01',
  endDate: '2024-12-31',
  initialCapital: 1000000,
  selectedStrategies: ['strategy_001'],
  period: '1d',
  maxPositionPerStock: 0.1,
  maxTotalPosition: 0.5,
  stopLoss: 0.02,
  maxDailyLoss: 0.02
})

const strategies = [
  { id: 'strategy_001', name: '双均线突破', desc: 'MA5/MA20交叉策略' },
  { id: 'strategy_002', name: 'MACD动量', desc: 'MACD柱状图动量策略' },
  { id: 'strategy_003', name: '布林带均值回归', desc: '布林带突破回归策略' },
  { id: 'strategy_004', name: 'RSI超买超卖', desc: 'RSI极端值反转策略' }
]

const history = [
  { id: 1, date: '2025-01-15 14:32', strategies: ['双均线突破'], return: 24.5 },
  { id: 2, date: '2025-01-14 10:15', strategies: ['MACD动量', 'RSI超买超卖'], return: 18.2 },
  { id: 3, date: '2025-01-13 16:45', strategies: ['布林带均值回归'], return: 31.8 },
  { id: 4, date: '2025-01-12 09:20', strategies: ['双均线突破', 'MACD动量'], return: -5.2 }
]

const summaryMetrics = computed(() => {
  if (!results.value) return []
  return [
    { label: '总收益率', value: `+${results.value.totalReturn}%`, positive: true },
    { label: '年化收益', value: `+${results.value.annualReturn}%`, positive: true },
    { label: '夏普比率', value: results.value.sharpe.toFixed(2) },
    { label: '最大回撤', value: `-${results.value.maxDrawdown}%`, negative: true },
    { label: '胜率', value: `${results.value.winRate}%` },
    { label: '交易次数', value: `${results.value.trades?.length || 0}笔` }
  ]
})

const displayedTrades = computed(() => {
  if (!results.value?.trades) return []
  return showAllTrades.value
    ? results.value.trades
    : results.value.trades.slice(0, 10)
})

async function startBacktest() {
  isRunning.value = true
  progress.value = 0

  // 模拟回测进度
  const steps = [
    { progress: 10, text: '加载历史数据...' },
    { progress: 30, text: '初始化策略...' },
    { progress: 50, text: '执行回测计算...' },
    { progress: 80, text: '生成报告...' },
    { progress: 100, text: '完成' }
  ]

  for (const step of steps) {
    await new Promise(r => setTimeout(r, 800))
    progress.value = step.progress
    loadingText.value = step.text
  }

  // 模拟回测结果
  results.value = {
    totalReturn: 24.58,
    annualReturn: 24.58,
    sharpe: 1.84,
    maxDrawdown: 8.50,
    winRate: 58.4,
    trades: [
      { id: 1, time: '2024-01-15 09:45:23', code: '600519.SH', direction: 'buy', price: 1685.00, qty: 100, pnl: 0 },
      { id: 2, time: '2024-02-20 14:32:15', code: '600519.SH', direction: 'sell', price: 1750.50, qty: 100, pnl: 6550 },
      { id: 3, time: '2024-03-05 10:15:42', code: '000858.SZ', direction: 'buy', price: 142.50, qty: 500, pnl: 0 },
      { id: 4, time: '2024-04-12 13:28:09', code: '000858.SZ', direction: 'sell', price: 138.20, qty: 500, pnl: -2150 },
      { id: 5, time: '2024-05-18 09:55:33', code: '300750.SZ', direction: 'buy', price: 198.00, qty: 200, pnl: 0 },
      { id: 6, time: '2024-06-22 15:00:00', code: '300750.SZ', direction: 'sell', price: 215.50, qty: 200, pnl: 3500 }
    ]
  }

  isRunning.value = false
}

function loadHistory(item: any) {
  // 加载历史回测结果
  console.log('Loading history:', item)
}

// 简化的图表绘制
watch(results, (newResults) => {
  if (newResults && chartCanvas.value) {
    drawChart()
  }
})

function drawChart() {
  const canvas = chartCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // 设置画布尺寸
  canvas.width = canvas.offsetWidth * 2
  canvas.height = canvas.offsetHeight * 2
  ctx.scale(2, 2)

  const width = canvas.offsetWidth
  const height = canvas.offsetHeight

  // 清除画布
  ctx.clearRect(0, 0, width, height)

  // 绘制网格
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'
  ctx.lineWidth = 1
  for (let i = 0; i <= 5; i++) {
    const y = (height - 40) * i / 5 + 20
    ctx.beginPath()
    ctx.moveTo(40, y)
    ctx.lineTo(width - 20, y)
    ctx.stroke()
  }

  // 绘制策略收益曲线（模拟）
  ctx.strokeStyle = '#f59e0b'
  ctx.lineWidth = 2
  ctx.beginPath()
  const points = 100
  for (let i = 0; i < points; i++) {
    const x = 40 + (width - 60) * i / (points - 1)
    const y = height - 20 - (height - 40) * (0.5 + 0.5 * Math.sin(i * 0.1) + i * 0.01) / 2
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.stroke()

  // 绘制基准收益曲线（模拟）
  ctx.strokeStyle = '#06b6d4'
  ctx.lineWidth = 2
  ctx.beginPath()
  for (let i = 0; i < points; i++) {
    const x = 40 + (width - 60) * i / (points - 1)
    const y = height - 20 - (height - 40) * (0.3 + i * 0.005) / 2
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.stroke()
}

onMounted(() => {
  if (results.value) {
    drawChart()
  }
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

.btn-primary:hover:not(:disabled) {
  background: #fbbf24;
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.btn-text {
  background: transparent;
  border: none;
  color: var(--accent-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.5rem;
}

.btn-text:hover {
  color: var(--accent-primary);
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

.backtest-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
}

.backtest-layout.with-history {
  grid-template-columns: 320px 1fr 280px;
}

.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
  margin-bottom: 1rem;
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

.panel-content {
  padding: 1.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.375rem;
}

.form-input,
.form-select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  color: var(--text-primary);
  font-size: 0.875rem;
  transition: all 0.15s ease;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.form-hint {
  display: block;
  font-size: 0.6875rem;
  color: var(--text-tertiary);
  margin-top: 0.25rem;
}

.input-with-prefix,
.input-with-suffix {
  position: relative;
}

.input-prefix,
.input-suffix {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.input-prefix {
  left: 0.75rem;
}

.input-suffix {
  right: 0.75rem;
}

.input-with-prefix .form-input {
  padding-left: 1.75rem;
}

.input-with-suffix .form-input {
  padding-right: 2rem;
}

.strategy-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.strategy-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.strategy-checkbox:hover,
.strategy-checkbox.selected {
  border-color: var(--accent-primary);
  background: rgba(245, 158, 11, 0.05);
}

.strategy-checkbox input {
  display: none;
}

.strategy-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.strategy-desc {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin-left: auto;
}

.empty-state {
  text-align: center;
  padding: 3rem;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-state p {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.progress-ring {
  position: relative;
  width: 100px;
  height: 100px;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--accent-primary);
}

.loading-text {
  margin-top: 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.metrics-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
}

.summary-card.positive {
  border-color: var(--accent-success);
  background: rgba(16, 185, 129, 0.05);
}

.summary-card.negative {
  border-color: var(--accent-danger);
  background: rgba(239, 68, 68, 0.05);
}

.summary-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.summary-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.summary-card.positive .summary-value {
  color: var(--accent-success);
}

.summary-card.negative .summary-value {
  color: var(--accent-danger);
}

.summary-subtext {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.chart-panel .panel-content {
  padding: 1rem;
}

.legend {
  display: flex;
  gap: 1rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-item.strategy .legend-dot {
  background: var(--accent-primary);
}

.legend-item.benchmark .legend-dot {
  background: var(--accent-secondary);
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

.data-table tr:last-child td {
  border-bottom: none;
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

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-primary);
}

.history-sidebar {
  position: fixed;
  right: 1.5rem;
  top: 140px;
  width: 260px;
  max-height: calc(100vh - 160px);
  overflow-y: auto;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.history-item:hover {
  border-color: var(--border-secondary);
  background: var(--bg-hover);
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.history-date {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.history-strategies {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.history-return {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 500;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.positive {
  color: var(--accent-success);
}

.negative {
  color: var(--accent-danger);
}

@media (max-width: 1200px) {
  .backtest-layout {
    grid-template-columns: 1fr;
  }

  .history-sidebar {
    position: static;
    width: 100%;
    max-height: none;
  }
}
</style>
