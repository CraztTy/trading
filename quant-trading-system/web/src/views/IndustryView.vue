<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">行业研究</h1>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="showReportModal = true">
          <span class="btn-icon">📄</span>
          生成报告
        </button>
      </div>
    </div>

    <div class="industry-layout">
      <!-- 行业选择 -->
      <div class="industry-sidebar">
        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">行业板块</h3>
          </div>
          <div class="panel-content">
            <div class="industry-list">
              <button
                v-for="industry in industries"
                :key="industry.id"
                class="industry-btn"
                :class="{ active: selectedIndustry?.id === industry.id }"
                @click="selectIndustry(industry)"
              >
                <span class="industry-icon">{{ industry.icon }}</span>
                <span class="industry-name">{{ industry.name }}</span>
                <span
                  class="industry-change"
                  :class="{ positive: industry.change > 0, negative: industry.change < 0 }"
                >
                  {{ industry.change > 0 ? '+' : '' }}{{ industry.change }}%
                </span>
              </button>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">行业热度</h3>
          </div>
          <div class="panel-content">
            <div class="heatmap">
              <div
                v-for="item in heatmapData"
                :key="item.name"
                class="heatmap-item"
                :style="{ background: getHeatColor(item.value) }"
              >
                <span class="heatmap-name">{{ item.name }}</span>
                <span class="heatmap-value">{{ item.value }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 行业详情 -->
      <div class="industry-content" v-if="selectedIndustry">
        <div class="industry-header">
          <div class="industry-title">
            <span class="title-icon">{{ selectedIndustry.icon }}</span>
            <div>
              <h2>{{ selectedIndustry.name }}</h2>
              <span class="industry-subtitle">{{ selectedIndustry.description }}</span>
            </div>
          </div>
          <div class="industry-metrics">
            <div class="metric">
              <span class="metric-label">涨跌</span>
              <span
                class="metric-value"
                :class="{ positive: selectedIndustry.change > 0, negative: selectedIndustry.change < 0 }"
              >
                {{ selectedIndustry.change > 0 ? '+' : '' }}{{ selectedIndustry.change }}%
              </span>
            </div>
            <div class="metric">
              <span class="metric-label">成交额</span>
              <span class="metric-value">{{ selectedIndustry.volume }}亿</span>
            </div>
            <div class="metric">
              <span class="metric-label">市盈率</span>
              <span class="metric-value">{{ selectedIndustry.pe }}倍</span>
            </div>
          </div>
        </div>

        <!-- 成分股表现 -->
        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">成分股表现</h3>
            <div class="panel-tabs">
              <button
                v-for="tab in stockTabs"
                :key="tab"
                class="panel-tab"
                :class="{ active: activeStockTab === tab }"
                @click="activeStockTab = tab"
              >
                {{ tab }}
              </button>
            </div>
          </div>
          <div class="panel-content">
            <table class="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>代码</th>
                  <th>名称</th>
                  <th>价格</th>
                  <th>涨跌</th>
                  <th>成交额</th>
                  <th>市值</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(stock, idx) in displayedStocks" :key="stock.code">
                  <td>
                    <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
                  </td>
                  <td class="mono">{{ stock.code }}</td>
                  <td>{{ stock.name }}</td>
                  <td class="mono">¥{{ stock.price.toFixed(2) }}</td>
                  <td
                    class="mono"
                    :class="{ positive: stock.change > 0, negative: stock.change < 0 }"
                  >
                    {{ stock.change > 0 ? '+' : '' }}{{ stock.change }}%
                  </td>
                  <td class="mono">{{ stock.volume }}亿</td>
                  <td class="mono">{{ stock.marketCap }}亿</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="analysis-grid">
          <!-- 投资逻辑 -->
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">投资逻辑</h3>
            </div>
            <div class="panel-content">
              <div class="logic-section">
                <h4 class="logic-title positive">
                  <span class="logic-icon">▲</span>
                  看多逻辑
                </h4>
                <ul class="logic-list">
                  <li v-for="item in industryLogic.bullish" :key="item">{{ item }}</li>
                </ul>
              </div>
              <div class="logic-section">
                <h4 class="logic-title negative">
                  <span class="logic-icon">▼</span>
                  看空逻辑
                </h4>
                <ul class="logic-list">
                  <li v-for="item in industryLogic.bearish" :key="item">{{ item }}</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- 产业链 -->
          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">产业链</h3>
            </div>
            <div class="panel-content">
              <div class="chain-flow">
                <div
                  v-for="(node, idx) in industryChain"
                  :key="node.name"
                  class="chain-node"
                >
                  <div class="node-content">
                    <span class="node-name">{{ node.name }}</span>
                    <span class="node-change" :class="{ positive: node.change > 0, negative: node.change < 0 }">
                      {{ node.change > 0 ? '+' : '' }}{{ node.change }}%
                    </span>
                  </div>
                  <span v-if="idx < industryChain.length - 1" class="chain-arrow">→</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 机构观点 -->
        <div class="panel">
          <div class="panel-header">
            <h3 class="panel-title">机构观点</h3>
            <span class="panel-badge">{{ institutions.length }} 家机构</span>
          </div>
          <div class="panel-content">
            <div class="institution-list">
              <div
                v-for="inst in institutions"
                :key="inst.name"
                class="institution-item"
              >
                <div class="inst-header">
                  <span class="inst-name">{{ inst.name }}</span>
                  <span class="inst-rating" :class="inst.rating">{{ inst.ratingText }}</span>
                </div>
                <p class="inst-comment">{{ inst.comment }}</p>
                <div class="inst-footer">
                  <span class="inst-target">目标价: ¥{{ inst.targetPrice }}</span>
                  <span class="inst-date">{{ inst.date }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="panel empty-panel">
        <div class="panel-content empty-state">
          <div class="empty-icon">🏭</div>
          <h3>选择行业</h3>
          <p>从左侧选择要研究的行业板块</p>
        </div>
      </div>
    </div>

    <!-- 报告弹窗 -->
    <div class="modal" v-if="showReportModal" @click.self="showReportModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>生成行业研究报告</h3>
          <button class="btn-icon-only" @click="showReportModal = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">选择行业</label>
            <select v-model="reportConfig.industry" class="form-select">
              <option v-for="ind in industries" :key="ind.id" :value="ind.id">
                {{ ind.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">报告类型</label>
            <div class="report-types">
              <label
                v-for="type in reportTypes"
                :key="type.id"
                class="report-type-option"
                :class="{ selected: reportConfig.type === type.id }"
              >
                <input type="radio" :value="type.id" v-model="reportConfig.type" />
                <span class="type-name">{{ type.name }}</span>
                <span class="type-desc">{{ type.description }}</span>
              </label>
            </div>
          </div>
          <button class="btn btn-primary full-width" @click="generateReport">
            生成报告
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const selectedIndustry = ref<any>(null)
const activeStockTab = ref('领涨')
const showReportModal = ref(false)

const industries = ref([
  { id: 'beverage', name: '白酒', icon: '🍶', description: '高端白酒及区域龙头', change: 2.35, volume: 285.6, pe: 28.5 },
  { id: 'semiconductor', name: '半导体', icon: '💻', description: '芯片设计及制造', change: -1.28, volume: 425.8, pe: 65.2 },
  { id: 'newenergy', name: '新能源', icon: '🔋', description: '光伏及锂电池产业链', change: 0.85, volume: 368.4, pe: 32.1 },
  { id: 'banking', name: '银行', icon: '🏦', description: '股份制及城商行', change: 0.52, volume: 156.3, pe: 5.8 },
  { id: 'pharmacy', name: '医药', icon: '💊', description: '创新药及医疗器械', change: -0.73, volume: 298.5, pe: 42.6 },
  { id: 'realestate', name: '房地产', icon: '🏠', description: '开发及物业管理', change: -2.15, volume: 125.4, pe: 12.3 }
])

const heatmapData = [
  { name: '白酒', value: 4.2 },
  { name: '保险', value: 2.8 },
  { name: '银行', value: 1.5 },
  { name: '医药', value: -0.8 },
  { name: '半导体', value: -2.3 },
  { name: '新能源', value: 0.5 },
  { name: '房地产', value: -3.5 },
  { name: '传媒', value: 3.2 },
  { name: '有色', value: 1.8 },
  { name: '化工', value: -1.2 }
]

const stockTabs = ['领涨', '领跌', '成交额']

const displayedStocks = ref([
  { code: '600519.SH', name: '贵州茅台', price: 1685.00, change: 3.25, volume: 45.2, marketCap: 21180 },
  { code: '000858.SZ', name: '五粮液', price: 142.50, change: 2.85, volume: 38.5, marketCap: 5528 },
  { code: '000568.SZ', name: '泸州老窖', price: 185.20, change: 2.12, volume: 28.6, marketCap: 2712 },
  { code: '600809.SH', name: '山西汾酒', price: 225.80, change: 1.95, volume: 22.4, marketCap: 2755 },
  { code: '002304.SZ', name: '洋河股份', price: 98.50, change: 1.28, volume: 18.2, marketCap: 1483 }
])

const industryLogic = ref({
  bullish: [
    '春节消费旺季临近，白酒需求预期向好',
    '茅台1935等产品打开次高端市场空间',
    '行业库存去化进展顺利，批价企稳回升'
  ],
  bearish: [
    '年轻消费群体偏好变化，需求结构分化',
    '部分区域酒企库存压力仍存',
    '宏观经济恢复不及预期影响商务消费'
  ]
})

const industryChain = [
  { name: '原料种植', change: 0.85 },
  { name: '原酒酿造', change: 2.35 },
  { name: '包装印刷', change: 1.25 },
  { name: '品牌销售', change: 2.85 },
  { name: '终端零售', change: 1.55 }
]

const institutions = ref([
  {
    name: '中信证券',
    rating: 'buy',
    ratingText: '买入',
    comment: '茅台1935持续放量，打开千元价格带增长空间，直营化率提升保障价格体系稳定。',
    targetPrice: 1850.00,
    date: '2025-01-10'
  },
  {
    name: '招商证券',
    rating: 'buy',
    ratingText: '买入',
    comment: '高端白酒需求韧性强，春节期间动销数据有望超预期，维持行业"推荐"评级。',
    targetPrice: 1900.00,
    date: '2025-01-08'
  },
  {
    name: '国泰君安',
    rating: 'hold',
    ratingText: '持有',
    comment: '当前估值已反映乐观预期，建议关注渠道库存变化及节后价格走势。',
    targetPrice: 1750.00,
    date: '2025-01-05'
  }
])

const reportTypes = [
  { id: 'overview', name: '行业概览', description: '包含行业基本情况、市场规模、竞争格局等' },
  { id: 'deep', name: '深度研究', description: '包含详细财务分析、产业链梳理、投资价值分析' },
  { id: 'tracking', name: '动态跟踪', description: '包含最新行业动态、政策解读、月度数据跟踪' }
]

const reportConfig = ref({
  industry: industries.value[0]?.id,
  type: 'overview'
})

function selectIndustry(industry: any) {
  selectedIndustry.value = industry
}

function getHeatColor(value: number) {
  const intensity = Math.min(Math.abs(value) / 5, 1)
  if (value > 0) {
    return `rgba(16, 185, 129, ${0.3 + intensity * 0.4})`
  } else {
    return `rgba(239, 68, 68, ${0.3 + intensity * 0.4})`
  }
}

function generateReport() {
  showReportModal.value = false
  // 模拟生成报告
  alert('报告生成中，请稍候...')
}

// 默认选中第一个行业
selectIndustry(industries.value[0])
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
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
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

.full-width {
  width: 100%;
}

.industry-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 1.5rem;
}

.industry-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  overflow: hidden;
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
  padding: 1rem;
}

.panel-tabs {
  display: flex;
  gap: 0.25rem;
}

.panel-tab {
  padding: 0.25rem 0.625rem;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
}

.panel-tab.active {
  background: var(--accent-primary);
  color: var(--bg-primary);
  border-color: var(--accent-primary);
}

.industry-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.industry-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.industry-btn:hover {
  background: var(--bg-hover);
}

.industry-btn.active {
  background: rgba(245, 158, 11, 0.1);
  border-color: var(--accent-primary);
}

.industry-icon {
  font-size: 1.25rem;
}

.industry-name {
  flex: 1;
  font-size: 0.875rem;
}

.industry-change {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  font-weight: 500;
}

.industry-change.positive {
  color: var(--accent-success);
}

.industry-change.negative {
  color: var(--accent-danger);
}

.heatmap {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.heatmap-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem;
  border-radius: 0.375rem;
}

.heatmap-name {
  font-size: 0.75rem;
  color: white;
}

.heatmap-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
}

.industry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  margin-bottom: 1.5rem;
}

.industry-title {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  font-size: 2.5rem;
}

.industry-title h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.industry-subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.industry-metrics {
  display: flex;
  gap: 2rem;
}

.metric {
  text-align: right;
}

.metric-label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin-bottom: 0.25rem;
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.metric-value.positive {
  color: var(--accent-success);
}

.metric-value.negative {
  color: var(--accent-danger);
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

.rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: var(--bg-tertiary);
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.rank.top {
  background: var(--accent-primary);
  color: var(--bg-primary);
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

.analysis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.logic-section {
  margin-bottom: 1.5rem;
}

.logic-section:last-child {
  margin-bottom: 0;
}

.logic-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.logic-title.positive {
  color: var(--accent-success);
}

.logic-title.negative {
  color: var(--accent-danger);
}

.logic-icon {
  font-size: 0.875rem;
}

.logic-list {
  list-style: none;
  padding: 0;
}

.logic-list li {
  padding: 0.5rem 0;
  padding-left: 1.25rem;
  font-size: 0.9375rem;
  color: var(--text-secondary);
  position: relative;
  border-bottom: 1px solid var(--border-primary);
}

.logic-list li:last-child {
  border-bottom: none;
}

.logic-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--accent-primary);
}

.chain-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.chain-node {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.node-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.875rem 1rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
  min-width: 80px;
}

.node-name {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.node-change {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 500;
}

.chain-arrow {
  font-size: 1.25rem;
  color: var(--text-muted);
}

.institution-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.institution-item {
  padding: 1rem;
  background: var(--bg-primary);
  border-radius: 0.5rem;
}

.inst-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.inst-name {
  font-weight: 500;
  color: var(--text-primary);
}

.inst-rating {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.inst-rating.buy {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.inst-rating.hold {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.inst-rating.sell {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.inst-comment {
  font-size: 0.9375rem;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  line-height: 1.5;
}

.inst-footer {
  display: flex;
  justify-content: space-between;
}

.inst-target {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8125rem;
  color: var(--accent-primary);
}

.inst-date {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.empty-panel {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-state p {
  font-size: 0.9375rem;
  color: var(--text-secondary);
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
  max-width: 500px;
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
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.375rem;
}

.form-select {
  width: 100%;
  padding: 0.625rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.form-select:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.report-types {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.report-type-option {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.875rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.report-type-option:hover,
.report-type-option.selected {
  border-color: var(--accent-primary);
  background: rgba(245, 158, 11, 0.05);
}

.report-type-option input {
  display: none;
}

.type-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
}

.type-desc {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

@media (max-width: 1200px) {
  .industry-layout {
    grid-template-columns: 1fr;
  }

  .industry-sidebar {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .industry-metrics {
    gap: 1rem;
  }
}

@media (max-width: 768px) {
  .industry-sidebar {
    grid-template-columns: 1fr;
  }

  .industry-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }

  .industry-title {
    flex-direction: column;
  }

  .industry-metrics {
    width: 100%;
    justify-content: space-around;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .chain-flow {
    flex-direction: column;
  }

  .chain-arrow {
    transform: rotate(90deg);
  }
}
</style>
