<template>
  <div class="animate-fade-in">
    <div class="page-header">
      <h1 class="page-title">智能分析</h1>
      <div class="page-actions">
        <button class="btn btn-secondary" @click="refreshAnalysis">
          <span class="btn-icon">↻</span>
          刷新分析
        </button>
      </div>
    </div>

    <div class="intelligence-grid">
      <!-- 分析类型选择 -->
      <div class="analysis-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-label">{{ tab.name }}</span>
        </button>
      </div>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          :placeholder="activeTab === 'fundamental' ? '输入股票代码或名称，如：贵州茅台' : '搜索行业或概念...'"
          @keyup.enter="performAnalysis"
        />
        <button class="btn btn-primary" @click="performAnalysis">
          <span class="btn-icon">🔍</span>
          分析
        </button>
      </div>

      <!-- 分析结果 -->
      <div class="analysis-content">
        <!-- 基本面分析 -->
        <template v-if="activeTab === 'fundamental' && analysisResult">
          <div class="result-header">
            <div class="company-info">
              <h2 class="company-name">{{ analysisResult.name }}</h2>
              <span class="company-code">{{ analysisResult.code }}</span>
            </div>
            <div class="analysis-score">
              <span class="score-label">综合评分</span>
              <span class="score-value" :class="getScoreClass(analysisResult.score)">
                {{ analysisResult.score }}
              </span>
            </div>
          </div>

          <div class="metrics-grid">
            <div
              v-for="metric in analysisResult.metrics"
              :key="metric.name"
              class="metric-card"
            >
              <span class="metric-name">{{ metric.name }}</span>
              <span class="metric-value">{{ metric.value }}</span>
              <span class="metric-trend" :class="metric.trend">
                {{ metric.trend === 'up' ? '↗' : metric.trend === 'down' ? '↘' : '→' }}
                {{ metric.change }}
              </span>
            </div>
          </div>

          <div class="analysis-panels">
            <div class="panel">
              <div class="panel-header">
                <h3 class="panel-title">财务健康度</h3>
              </div>
              <div class="panel-content">
                <div class="health-chart">
                  <div
                    v-for="item in analysisResult.healthIndicators"
                    :key="item.name"
                    class="health-item"
                  >
                    <div class="health-header">
                      <span class="health-name">{{ item.name }}</span>
                      <span class="health-score" :class="getScoreClass(item.score)">
                        {{ item.score }}分
                      </span>
                    </div>
                    <div class="health-bar">
                      <div
                        class="health-fill"
                        :style="{ width: item.score + '%' }"
                        :class="getScoreClass(item.score)"
                      ></div>
                    </div>
                    <span class="health-desc">{{ item.description }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="panel">
              <div class="panel-header">
                <h3 class="panel-title">分析报告</h3>
              </div>
              <div class="panel-content">
                <div class="report-content">
                  <p v-for="(paragraph, idx) in analysisResult.report" :key="idx">
                    {{ paragraph }}
                  </p>
                </div>
                <div class="report-tags">
                  <span
                    v-for="tag in analysisResult.tags"
                    :key="tag"
                    class="report-tag"
                    :class="tag.type"
                  >
                    {{ tag.name }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <h3 class="panel-title">风险与机会</h3>
            </div>
            <div class="panel-content">
              <div class="risk-opportunity-grid">
                <div class="risk-section">
                  <h4 class="section-title">
                    <span class="section-icon">⚠</span>
                    风险点
                  </h4>
                  <ul class="risk-list">
                    <li v-for="risk in analysisResult.risks" :key="risk">
                      {{ risk }}
                    </li>
                  </ul>
                </div>
                <div class="opportunity-section">
                  <h4 class="section-title">
                    <span class="section-icon">💡</span>
                    机会点
                  </h4>
                  <ul class="opportunity-list">
                    <li v-for="opp in analysisResult.opportunities" :key="opp">
                      {{ opp }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 选股筛选 -->
        <template v-if="activeTab === 'screener'">
          <div class="screener-layout">
            <div class="screener-filters">
              <div class="panel">
                <div class="panel-header">
                  <h3 class="panel-title">筛选条件</h3>
                  <button class="btn-text" @click="resetFilters">重置</button>
                </div>
                <div class="panel-content">
                  <div class="filter-group">
                    <label class="filter-label">市盈率 (PE)</label>
                    <div class="range-inputs">
                      <input v-model.number="filters.peMin" type="number" placeholder="最小" class="filter-input" />
                      <span>-</span>
                      <input v-model.number="filters.peMax" type="number" placeholder="最大" class="filter-input" />
                    </div>
                  </div>

                  <div class="filter-group">
                    <label class="filter-label">市净率 (PB)</label>
                    <div class="range-inputs">
                      <input v-model.number="filters.pbMin" type="number" placeholder="最小" class="filter-input" />
                      <span>-</span>
                      <input v-model.number="filters.pbMax" type="number" placeholder="最大" class="filter-input" />
                    </div>
                  </div>

                  <div class="filter-group">
                    <label class="filter-label">ROE (%)</label>
                    <div class="range-inputs">
                      <input v-model.number="filters.roeMin" type="number" placeholder="最小" class="filter-input" />
                      <span>-</span>
                      <input v-model.number="filters.roeMax" type="number" placeholder="最大" class="filter-input" />
                    </div>
                  </div>

                  <div class="filter-group">
                    <label class="filter-label">股息率 (%)</label>
                    <div class="range-inputs">
                      <input v-model.number="filters.dividendMin" type="number" placeholder="最小" class="filter-input" />
                      <span>-</span>
                      <input v-model.number="filters.dividendMax" type="number" placeholder="最大" class="filter-input" />
                    </div>
                  </div>

                  <div class="filter-group">
                    <label class="filter-label">市值 (亿)</label>
                    <div class="range-inputs">
                      <input v-model.number="filters.marketCapMin" type="number" placeholder="最小" class="filter-input" />
                      <span>-</span>
                      <input v-model.number="filters.marketCapMax" type="number" placeholder="最大" class="filter-input" />
                    </div>
                  </div>

                  <button class="btn btn-primary full-width" @click="runScreener">
                    执行筛选
                  </button>
                </div>
              </div>
            </div>

            <div class="screener-results">
              <div class="panel">
                <div class="panel-header">
                  <h3 class="panel-title">筛选结果</h3>
                  <span class="panel-badge">{{ screenerResults.length }} 只股票</span>
                </div>
                <div class="panel-content">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>PE</th>
                        <th>PB</th>
                        <th>ROE</th>
                        <th>股息率</th>
                        <th>市值</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="stock in screenerResults" :key="stock.code" @click="viewStock(stock)">
                        <td class="mono">{{ stock.code }}</td>
                        <td>{{ stock.name }}</td>
                        <td class="mono">{{ stock.pe.toFixed(2) }}</td>
                        <td class="mono">{{ stock.pb.toFixed(2) }}</td>
                        <td class="mono">{{ stock.roe.toFixed(2) }}%</td>
                        <td class="mono">{{ stock.dividend.toFixed(2) }}%</td>
                        <td class="mono">{{ stock.marketCap }}亿</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 空状态 -->
        <div v-if="!analysisResult && activeTab === 'fundamental'" class="empty-state">
          <div class="empty-icon">📊</div>
          <h3>智能基本面分析</h3>
          <p>输入股票代码获取深度财务分析和投资建议</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

const activeTab = ref('fundamental')
const searchQuery = ref('')
const analysisResult = ref<any>(null)

const tabs = [
  { id: 'fundamental', name: '基本面分析', icon: '📈' },
  { id: 'screener', name: '智能选股', icon: '🔍' },
  { id: 'technical', name: '技术面分析', icon: '📉' },
  { id: 'sentiment', name: '情绪分析', icon: '😊' }
]

const filters = reactive({
  peMin: null,
  peMax: 30,
  pbMin: null,
  pbMax: 3,
  roeMin: 10,
  roeMax: null,
  dividendMin: 2,
  dividendMax: null,
  marketCapMin: 100,
  marketCapMax: null
})

const screenerResults = ref([
  { code: '600519.SH', name: '贵州茅台', pe: 28.5, pb: 8.2, roe: 25.5, dividend: 1.5, marketCap: 21000 },
  { code: '000858.SZ', name: '五粮液', pe: 22.3, pb: 5.8, roe: 22.1, dividend: 2.1, marketCap: 5500 },
  { code: '000333.SZ', name: '美的集团', pe: 15.2, pb: 3.2, roe: 18.5, dividend: 3.2, marketCap: 4200 },
  { code: '600036.SH', name: '招商银行', pe: 8.5, pb: 1.2, roe: 15.8, dividend: 4.5, marketCap: 8500 },
  { code: '601318.SH', name: '中国平安', pe: 12.3, pb: 1.5, roe: 18.2, dividend: 3.8, marketCap: 9200 }
])

function performAnalysis() {
  // 模拟分析结果
  analysisResult.value = {
    name: '贵州茅台',
    code: '600519.SH',
    score: 85,
    metrics: [
      { name: '市盈率', value: '28.5', change: '2.1%', trend: 'down' },
      { name: '市净率', value: '8.2', change: '0.5%', trend: 'up' },
      { name: 'ROE', value: '25.5%', change: '1.2%', trend: 'up' },
      { name: '毛利率', value: '91.5%', change: '0.3%', trend: 'up' }
    ],
    healthIndicators: [
      { name: '盈利能力', score: 95, description: '净利润率持续领先' },
      { name: '偿债能力', score: 88, description: '资产负债结构健康' },
      { name: '成长性', score: 75, description: '营收增速放缓' },
      { name: '运营效率', score: 82, description: '存货周转良好' }
    ],
    report: [
      '贵州茅台2024年财报表现稳健，全年实现营收1505亿元，同比增长17.5%；净利润747亿元，同比增长19.2%。',
      '公司核心竞争优势依然明显，茅台酒品牌溢价能力强，毛利率维持在91%以上的高位。',
      '渠道改革持续推进，直营化率提升至45%，有效保障了价格体系的稳定。'
    ],
    tags: [
      { name: '优质白马', type: 'positive' },
      { name: '价值投资', type: 'positive' },
      { name: '消费龙头', type: 'neutral' }
    ],
    risks: [
      '估值处于历史较高分位，PE超过30倍',
      '消费需求复苏不及预期',
      '渠道库存压力有所增加'
    ],
    opportunities: [
      '茅台1935等产品打开次高端市场',
      '直营化提升终端价格管控能力',
      '分红比例提升预期'
    ]
  }
}

function refreshAnalysis() {
  if (searchQuery.value) {
    performAnalysis()
  }
}

function getScoreClass(score: number) {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  return 'average'
}

function resetFilters() {
  Object.keys(filters).forEach(key => {
    (filters as any)[key] = null
  })
}

function runScreener() {
  // 模拟筛选
  console.log('Running screener with filters:', filters)
}

function viewStock(stock: any) {
  activeTab.value = 'fundamental'
  searchQuery.value = stock.code
  performAnalysis()
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

.full-width {
  width: 100%;
}

.intelligence-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.analysis-tabs {
  display: flex;
  gap: 0.5rem;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  border-color: var(--border-secondary);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: var(--bg-primary);
}

.tab-icon {
  font-size: 1rem;
}

.search-bar {
  display: flex;
  gap: 0.75rem;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.9375rem;
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.analysis-content {
  min-height: 400px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  margin-bottom: 1.5rem;
}

.company-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.company-name {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
}

.company-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  background: var(--bg-tertiary);
  border-radius: 0.25rem;
}

.analysis-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.score-label {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.score-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2.5rem;
  font-weight: 700;
}

.score-value.excellent {
  color: var(--accent-success);
}

.score-value.good {
  color: var(--accent-primary);
}

.score-value.average {
  color: var(--accent-warning);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.5rem;
}

.metric-name {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.metric-trend {
  font-size: 0.8125rem;
}

.metric-trend.up {
  color: var(--accent-success);
}

.metric-trend.down {
  color: var(--accent-danger);
}

.analysis-panels {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
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
  padding: 1.25rem;
}

.health-chart {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.health-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.health-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-name {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.health-score {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 500;
}

.health-score.excellent {
  color: var(--accent-success);
}

.health-score.good {
  color: var(--accent-primary);
}

.health-bar {
  height: 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  overflow: hidden;
}

.health-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.health-fill.excellent {
  background: var(--accent-success);
}

.health-fill.good {
  background: var(--accent-primary);
}

.health-fill.average {
  background: var(--accent-warning);
}

.health-desc {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.report-content {
  margin-bottom: 1rem;
}

.report-content p {
  font-size: 0.9375rem;
  line-height: 1.7;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}

.report-content p:last-child {
  margin-bottom: 0;
}

.report-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.report-tag {
  padding: 0.375rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.8125rem;
}

.report-tag.positive {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.report-tag.neutral {
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.risk-opportunity-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.risk-section .section-icon {
  color: var(--accent-warning);
}

.opportunity-section .section-icon {
  color: var(--accent-success);
}

.risk-list,
.opportunity-list {
  list-style: none;
  padding: 0;
}

.risk-list li,
.opportunity-list li {
  padding: 0.625rem 0;
  padding-left: 1.25rem;
  position: relative;
  font-size: 0.9375rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.risk-list li:last-child,
.opportunity-list li:last-child {
  border-bottom: none;
}

.risk-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--accent-warning);
}

.opportunity-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--accent-success);
}

.screener-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1.5rem;
}

.filter-group {
  margin-bottom: 1rem;
}

.filter-label {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-bottom: 0.375rem;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.range-inputs span {
  color: var(--text-tertiary);
}

.filter-input {
  flex: 1;
  padding: 0.5rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 0.375rem;
  color: var(--text-primary);
  font-size: 0.8125rem;
}

.filter-input:focus {
  outline: none;
  border-color: var(--accent-primary);
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

.data-table tr:hover td {
  background: var(--bg-hover);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.empty-state {
  text-align: center;
  padding: 4rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
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

@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .analysis-panels {
    grid-template-columns: 1fr;
  }

  .screener-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .risk-opportunity-grid {
    grid-template-columns: 1fr;
  }

  .analysis-tabs {
    flex-wrap: wrap;
  }
}
</style>
