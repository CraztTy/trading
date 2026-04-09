<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">宏观分析</h1>
      <div class="page-actions">
        <span class="update-time">数据更新: {{ lastUpdate }}</span>
        <button class="btn btn-secondary" @click="refreshData">
          <span class="btn-icon">↻</span>
          刷新
        </button>
      </div>
    </div>

    <div class="macro-layout">
      <!-- 左侧：经济指标 -->
      <div class="macro-left">
        <!-- 经济周期判断 -->
        <div class="panel cycle-panel">
          <div class="panel-header">
            <h3 class="panel-title">经济周期</h3>
            <span class="panel-badge" :class="cycleData.phase">
              {{ cyclePhaseText }}
            </span>
          </div>
          <div class="panel-content">
            <div class="cycle-visual">
              <div class="cycle-ring">
                <div
                  v-for="(phase, idx) in cyclePhases"
                  :key="phase.id"
                  class="cycle-phase"
                  :class="{ active: cycleData.phase === phase.id }"
                  :style="getCyclePosition(idx)"
                >
                  <span class="phase-name">{{ phase.name }}</span>
                </div>
                <div class="cycle-center">
                  <span class="cycle-indicator">{{ cycleIndicator }}</span>
                </div>
              </div>
            </div>
            <div class="cycle-description">
              <p>{{ cycleData.description }}</p>
              <div class="cycle-implications">
                <h4>市场影响</h4>
                <ul>
                  <li v-for="imp in cycleData.implications" :key="imp">{{ imp }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- 关键指标 -->
        <div class="panel indicators-panel">
          <div class="panel-header">
            <h3 class="panel-title">关键经济指标</h3>
          </div>
          <div class="panel-content">
            <div class="indicators-grid">
              <div
                v-for="indicator in keyIndicators"
                :key="indicator.name"
                class="indicator-card"
                :class="indicator.trend"
              >
                <div class="indicator-header">
                  <span class="indicator-name">{{ indicator.name }}</span>
                  <span class="indicator-period">{{ indicator.period }}</span>
                </div>
                <div class="indicator-value">
                  <span class="value">{{ indicator.value }}</span>
                  <span class="unit">{{ indicator.unit }}</span>
                </div>
                <div class="indicator-change" :class="indicator.changeType">
                  <span class="arrow">{{ indicator.changeType === 'up' ? '↗' : '↘' }}</span>
                  {{ indicator.change }}
                </div>
                <div class="indicator-chart">
                  <svg viewBox="0 0 100 30" preserveAspectRatio="none">
                    <polyline
                      :points="indicator.sparkline"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：政策与情绪 -->
      <div class="macro-right">
        <!-- 货币政策 -->
        <div class="panel policy-panel">
          <div class="panel-header">
            <h3 class="panel-title">货币政策</h3>
            <span class="policy-status" :class="policyData.stance">
              {{ policyStanceText }}
            </span>
          </div>
          <div class="panel-content">
            <div class="policy-rates">
              <div
                v-for="rate in policyRates"
                :key="rate.name"
                class="rate-item"
              >
                <span class="rate-name">{{ rate.name }}</span>
                <div class="rate-value">
                  <span class="current">{{ rate.current }}%</span>
                  <span class="change" :class="rate.trend">
                    {{ rate.change > 0 ? '+' : '' }}{{ rate.change }}bp
                  </span>
                </div>
                <div class="rate-history">
                  <div
                    v-for="(h, idx) in rate.history"
                    :key="idx"
                    class="history-dot"
                    :class="h.type"
                    :title="h.date"
                  ></div>
                </div>
              </div>
            </div>
            <div class="policy-analysis">
              <h4>政策解读</h4>
              <p>{{ policyData.analysis }}</p>
            </div>
          </div>
        </div>

        <!-- 市场情绪 -->
        <div class="panel sentiment-panel">
          <div class="panel-header">
            <h3 class="panel-title">市场情绪指数</h3>
          </div>
          <div class="panel-content">
            <div class="sentiment-gauge">
              <div class="gauge-container">
                <svg viewBox="0 0 200 120" class="gauge-svg">
                  <defs>
                    <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#ef4444" />
                      <stop offset="50%" stop-color="#f59e0b" />
                      <stop offset="100%" stop-color="#10b981" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M 20 100 A 80 80 0 0 1 180 100"
                    fill="none"
                    stroke="url(#gaugeGradient)"
                    stroke-width="20"
                    stroke-linecap="round"
                  />
                  <line
                    :x1="getGaugeX(sentimentData.value)"
                    :y1="getGaugeY(sentimentData.value)"
                    x2="100"
                    y2="100"
                    stroke="white"
                    stroke-width="3"
                    stroke-linecap="round"
                  />
                  <circle cx="100" cy="100" r="8" fill="white" />
                </svg>
                <div class="gauge-value">
                  <span class="value">{{ sentimentData.value }}</span>
                  <span class="label">{{ sentimentLabel }}</span>
                </div>
              </div>
              <div class="sentiment-factors">
                <div
                  v-for="factor in sentimentFactors"
                  :key="factor.name"
                  class="factor-item"
                >
                  <span class="factor-name">{{ factor.name }}</span>
                  <div class="factor-bar">
                    <div
                      class="factor-fill"
                      :style="{ width: factor.value + '%', background: factor.color }"
                    ></div>
                  </div>
                  <span class="factor-value">{{ factor.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 资金流向 -->
        <div class="panel flow-panel">
          <div class="panel-header">
            <h3 class="panel-title">资金流向</h3>
            <div class="flow-tabs">
              <button
                v-for="tab in flowTabs"
                :key="tab"
                class="flow-tab"
                :class="{ active: activeFlowTab === tab }"
                @click="activeFlowTab = tab"
              >
                {{ tab }}
              </button>
            </div>
          </div>
          <div class="panel-content">
            <div class="flow-summary">
              <div class="flow-item inflow">
                <span class="flow-label">净流入</span>
                <span class="flow-value">+{{ flowData.inflow }}亿</span>
              </div>
              <div class="flow-item outflow">
                <span class="flow-label">净流出</span>
                <span class="flow-value">-{{ flowData.outflow }}亿</span>
              </div>
              <div class="flow-item net" :class="flowData.net > 0 ? 'positive' : 'negative'">
                <span class="flow-label">净流向</span>
                <span class="flow-value">{{ flowData.net > 0 ? '+' : '' }}{{ flowData.net }}亿</span>
              </div>
            </div>
            <div class="flow-sectors">
              <div
                v-for="sector in flowData.sectors"
                :key="sector.name"
                class="sector-flow"
              >
                <span class="sector-name">{{ sector.name }}</span>
                <div class="sector-bar">
                  <div
                    class="sector-fill"
                    :style="{ width: Math.abs(sector.flow) / 50 + '%' }"
                    :class="sector.flow > 0 ? 'positive' : 'negative'"
                  ></div>
                </div>
                <span class="sector-value" :class="sector.flow > 0 ? 'positive' : 'negative'">
                  {{ sector.flow > 0 ? '+' : '' }}{{ sector.flow }}亿
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
import { ref, computed } from 'vue'

const lastUpdate = ref('2025-01-15 10:30:00')
const activeFlowTab = ref('今日')

const cycleData = ref({
  phase: 'expansion',
  description: '当前经济处于扩张期，GDP增速回升至5%以上，制造业PMI连续3个月位于荣枯线上方，企业盈利改善，就业市场稳健。',
  implications: [
    '权益资产受益，建议增配股票',
    '周期股表现优于防御股',
    '利率上行压力增加，债券需谨慎',
    '大宗商品需求回暖'
  ]
})

const cyclePhases = [
  { id: 'recovery', name: '复苏' },
  { id: 'expansion', name: '扩张' },
  { id: 'slowdown', name: '放缓' },
  { id: 'recession', name: '衰退' }
]

const cyclePhaseText = computed(() => {
  const map: Record<string, string> = {
    recovery: '复苏期',
    expansion: '扩张期',
    slowdown: '放缓期',
    recession: '衰退期'
  }
  return map[cycleData.value.phase] || '未知'
})

const cycleIndicator = computed(() => {
  return cyclePhases.find(p => p.id === cycleData.value.phase)?.name || '?'
})

function getCyclePosition(idx: number) {
  const angle = idx * 90 - 45
  const radius = 70
  const x = 50 + radius * Math.cos((angle * Math.PI) / 180)
  const y = 50 + radius * Math.sin((angle * Math.PI) / 180)
  return {
    left: `${x}%`,
    top: `${y}%`,
    transform: 'translate(-50%, -50%)'
  }
}

const keyIndicators = ref([
  { name: 'GDP同比', value: '5.2', unit: '%', change: '+0.3%', changeType: 'up', period: '2024Q4', trend: 'positive', sparkline: '0,20 20,18 40,22 60,15 80,12 100,10' },
  { name: 'CPI同比', value: '0.3', unit: '%', change: '+0.1%', changeType: 'up', period: '2024年12月', trend: 'neutral', sparkline: '0,25 20,28 40,26 60,30 80,28 100,27' },
  { name: '制造业PMI', value: '50.8', unit: '', change: '+0.2', changeType: 'up', period: '2024年12月', trend: 'positive', sparkline: '0,30 20,28 40,25 60,22 80,20 100,18' },
  { name: '社会融资规模', value: '29.4', unit: '万亿', change: '+9.5%', changeType: 'up', period: '2024年', trend: 'positive', sparkline: '0,25 20,23 40,20 60,18 80,15 100,12' },
  { name: '失业率', value: '5.0', unit: '%', change: '-0.1%', changeType: 'down', period: '2024年12月', trend: 'positive', sparkline: '0,15 20,18 40,20 60,22 80,25 100,28' },
  { name: 'M2同比', value: '8.7', unit: '%', change: '-0.3%', changeType: 'down', period: '2024年12月', trend: 'neutral', sparkline: '0,20 20,22 40,24 60,26 80,28 100,30' }
])

const policyData = ref({
  stance: 'neutral',
  analysis: '当前货币政策保持中性偏松，央行通过MLF和逆回购操作维持市场流动性合理充裕。LPR连续保持稳定，显示政策利率锚定效应明显。预计短期内货币政策将保持定力，重点在于疏通传导机制，引导资金流向实体经济。'
})

const policyStanceText = computed(() => {
  const map: Record<string, string> = {
    loose: '宽松',
    neutral: '中性',
    tight: '紧缩'
  }
  return map[policyData.value.stance] || '未知'
})

const policyRates = ref([
  {
    name: '1年期LPR',
    current: 3.45,
    change: 0,
    trend: 'stable',
    history: [
      { date: '2024-01', type: 'stable' },
      { date: '2024-02', type: 'stable' },
      { date: '2024-03', type: 'stable' },
      { date: '2024-04', type: 'stable' },
      { date: '2024-05', type: 'stable' }
    ]
  },
  {
    name: '5年期LPR',
    current: 4.20,
    change: -25,
    trend: 'down',
    history: [
      { date: '2024-01', type: 'stable' },
      { date: '2024-02', type: 'cut' },
      { date: '2024-03', type: 'stable' },
      { date: '2024-04', type: 'stable' },
      { date: '2024-05', type: 'stable' }
    ]
  },
  {
    name: 'MLF利率',
    current: 2.50,
    change: 0,
    trend: 'stable',
    history: [
      { date: '2024-01', type: 'stable' },
      { date: '2024-02', type: 'cut' },
      { date: '2024-03', type: 'stable' },
      { date: '2024-04', type: 'stable' },
      { date: '2024-05', type: 'stable' }
    ]
  }
])

const sentimentData = ref({
  value: 68,
  label: '偏乐观'
})

const sentimentLabel = computed(() => {
  if (sentimentData.value >= 80) return '极度乐观'
  if (sentimentData.value >= 60) return '偏乐观'
  if (sentimentData.value >= 40) return '中性'
  if (sentimentData.value >= 20) return '偏悲观'
  return '极度悲观'
})

function getGaugeX(value: number) {
  const angle = (value / 100) * 180 - 180
  return 100 + 80 * Math.cos((angle * Math.PI) / 180)
}

function getGaugeY(value: number) {
  const angle = (value / 100) * 180 - 180
  return 100 + 80 * Math.sin((angle * Math.PI) / 180)
}

const sentimentFactors = ref([
  { name: '投资者信心', value: 72, color: '#10b981' },
  { name: '机构调研热度', value: 65, color: '#f59e0b' },
  { name: '融资买入占比', value: 58, color: '#f59e0b' },
  { name: '新基金发行', value: 45, color: '#ef4444' }
])

const flowTabs = ['今日', '5日', '20日']

const flowData = ref({
  inflow: 1258,
  outflow: 1189,
  net: 69,
  sectors: [
    { name: '电子', flow: 45.2 },
    { name: '医药生物', flow: 32.8 },
    { name: '食品饮料', flow: 28.5 },
    { name: '电力设备', flow: -18.3 },
    { name: '银行', flow: -25.6 },
    { name: '房地产', flow: -38.9 }
  ]
})

function refreshData() {
  lastUpdate.value = new Date().toLocaleString('zh-CN')
}
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

.update-time {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
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

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--border-secondary);
}

.macro-layout {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 1.5rem;
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
  border-radius: 0.25rem;
  font-weight: 500;
}

.panel-badge.recovery {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.panel-badge.expansion {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-primary);
}

.panel-badge.slowdown {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.panel-badge.recession {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.panel-content {
  padding: 1.25rem;
}

.cycle-visual {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 1.5rem;
}

.cycle-ring {
  position: relative;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 4px solid var(--border-primary);
}

.cycle-phase {
  position: absolute;
  padding: 0.5rem 0.75rem;
  background: var(--bg-tertiary);
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  transition: all 0.3s ease;
}

.cycle-phase.active {
  background: var(--accent-primary);
  color: var(--bg-primary);
  font-weight: 500;
}

.cycle-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border-radius: 50%;
  border: 2px solid var(--border-primary);
}

.cycle-indicator {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--accent-primary);
}

.cycle-description p {
  font-size: 0.9375rem;
  line-height: 1.7;
  color: var(--text-secondary);
  margin-bottom: 1rem;
}

.cycle-implications h4 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.cycle-implications ul {
  list-style: none;
  padding: 0;
}

.cycle-implications li {
  padding: 0.375rem 0;
  padding-left: 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  position: relative;
}

.cycle-implications li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: var(--accent-primary);
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.indicator-card {
  padding: 1rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
  border: 1px solid var(--border-primary);
}

.indicator-card.positive {
  border-color: rgba(16, 185, 129, 0.3);
}

.indicator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.indicator-name {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.indicator-period {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
}

.indicator-value {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
}

.indicator-value .value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
}

.indicator-value .unit {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.indicator-change {
  font-size: 0.8125rem;
  margin-bottom: 0.5rem;
}

.indicator-change.up {
  color: var(--accent-success);
}

.indicator-change.down {
  color: var(--accent-danger);
}

.indicator-chart {
  height: 30px;
  color: var(--accent-primary);
}

.indicator-chart svg {
  width: 100%;
  height: 100%;
}

.policy-status {
  font-size: 0.8125rem;
  padding: 0.25rem 0.625rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

.policy-status.loose {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.policy-status.neutral {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.policy-status.tight {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.policy-rates {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.rate-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
}

.rate-name {
  width: 80px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.rate-value {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.rate-value .current {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.rate-value .change {
  font-size: 0.75rem;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
}

.rate-value .change.stable {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

.rate-value .change.down {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.rate-value .change.up {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.rate-history {
  display: flex;
  gap: 0.375rem;
}

.history-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.history-dot.stable {
  background: var(--text-muted);
}

.history-dot.cut {
  background: var(--accent-success);
}

.history-dot.hike {
  background: var(--accent-danger);
}

.policy-analysis h4 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.policy-analysis p {
  font-size: 0.9375rem;
  line-height: 1.7;
  color: var(--text-secondary);
}

.sentiment-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-container {
  position: relative;
  width: 200px;
  margin-bottom: 1.5rem;
}

.gauge-svg {
  width: 100%;
  height: 120px;
}

.gauge-value {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
}

.gauge-value .value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2rem;
  font-weight: 700;
  color: var(--accent-primary);
}

.gauge-value .label {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.sentiment-factors {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.factor-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.factor-name {
  width: 100px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.factor-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}

.factor-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.factor-value {
  width: 32px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  text-align: right;
}

.flow-tabs {
  display: flex;
  gap: 0.25rem;
}

.flow-tab {
  padding: 0.25rem 0.625rem;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.flow-tab:hover {
  border-color: var(--border-secondary);
  color: var(--text-primary);
}

.flow-tab.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: var(--bg-primary);
}

.flow-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.flow-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
  text-align: center;
}

.flow-label {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.flow-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 600;
}

.flow-item.inflow .flow-value {
  color: var(--accent-success);
}

.flow-item.outflow .flow-value {
  color: var(--accent-danger);
}

.flow-item.net.positive .flow-value {
  color: var(--accent-success);
}

.flow-item.net.negative .flow-value {
  color: var(--accent-danger);
}

.flow-sectors {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sector-flow {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sector-name {
  width: 80px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.sector-bar {
  flex: 1;
  height: 20px;
  background: var(--bg-primary);
  border-radius: 0.25rem;
  overflow: hidden;
  position: relative;
}

.sector-fill {
  height: 100%;
  min-width: 2px;
  transition: width 0.3s ease;
}

.sector-fill.positive {
  background: var(--accent-success);
}

.sector-fill.negative {
  background: var(--accent-danger);
}

.sector-value {
  width: 70px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  text-align: right;
}

.sector-value.positive {
  color: var(--accent-success);
}

.sector-value.negative {
  color: var(--accent-danger);
}

@media (max-width: 1200px) {
  .macro-layout {
    grid-template-columns: 1fr;
  }

  .indicators-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .indicators-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .flow-summary {
    grid-template-columns: 1fr;
  }
}
</style>
