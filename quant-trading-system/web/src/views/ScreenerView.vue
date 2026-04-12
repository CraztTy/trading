<template>
  <div class="screener-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">AI 智能选股</h1>
        <p class="page-subtitle">自然语言筛选，精准定位投资机会</p>
      </div>
      <div class="ai-status">
        <span class="ai-dot"></span>
        <span class="ai-text">AI 引擎运行中</span>
      </div>
    </div>

    <!-- 自然语言输入 -->
    <div class="nl-input-section">
      <div class="input-wrapper">
        <el-icon class="input-icon"><Microphone /></el-icon>
        <input
          v-model="nlQuery"
          type="text"
          placeholder="例如：查找市盈率低于20的蓝筹股，或者近一个月涨幅超过10%的科技股票..."
          class="nl-input"
          @keyup.enter="runScreening"
        />
        <button class="search-btn" @click="runScreening" :disabled="loading">
          <el-icon><Loading v-if="loading" /><Search v-else /></el-icon>
          <span>{{ loading ? '筛选中...' : '智能筛选' }}</span>
        </button>
      </div>

      <!-- 快捷筛选 -->
      <div class="quick-filters">
        <span class="filter-label">快捷筛选:</span>
        <button
          v-for="filter in quickFilters"
          :key="filter.id"
          class="filter-chip"
          @click="applyFilter(filter)"
        >
          {{ filter.name }}
        </button>
      </div>
    </div>

    <!-- 筛选条件面板 -->
    <div class="filters-panel">
      <div class="panel-section">
        <h3 class="section-title">估值指标</h3>
        <div class="filter-row">
          <div class="filter-item">
            <label>市盈率 (PE)</label>
            <el-slider v-model="filters.pe" range :max="100" :marks="{0: '0', 50: '50', 100: '100'}" />
          </div>
          <div class="filter-item">
            <label>市净率 (PB)</label>
            <el-slider v-model="filters.pb" range :max="10" :step="0.1" :marks="{0: '0', 5: '5', 10: '10'}" />
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">盈利能力</h3>
        <div class="filter-row">
          <div class="filter-item">
            <label>ROE (%)</label>
            <el-slider v-model="filters.roe" range :max="50" :marks="{0: '0', 25: '25', 50: '50'}" />
          </div>
          <div class="filter-item">
            <label>净利润增长率 (%)</label>
            <el-slider v-model="filters.profitGrowth" range :min="-50" :max="100" />
          </div>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">市场表现</h3>
        <div class="filter-row">
          <div class="filter-item">
            <label>近一月涨幅 (%)</label>
            <el-slider v-model="filters.monthReturn" range :min="-30" :max="50" />
          </div>
          <div class="filter-item">
            <label>市值范围 (亿)</label>
            <el-slider v-model="filters.marketCap" range :max="10000" :step="100" :marks="{0: '0', 5000: '5000', 10000: '10000+'}" />
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选结果 -->
    <div class="results-section">
      <div class="results-header">
        <div class="results-count">
          找到 <span class="count">{{ totalCount }}</span> 只股票
          <span v-if="executionTime > 0" class="execution-time">({{ executionTime.toFixed(1) }}ms)</span>
        </div>
        <div class="results-actions">
          <el-radio-group v-model="sortBy" size="small">
            <el-radio-button label="score">综合评分</el-radio-button>
            <el-radio-button label="pe">市盈率</el-radio-button>
            <el-radio-button label="roe">ROE</el-radio-button>
            <el-radio-button label="return">涨跌幅</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <div class="stocks-grid">
        <div
          v-for="stock in screenedStocks"
          :key="stock.symbol"
          class="stock-card"
        >
          <div class="card-header">
            <div class="stock-info">
              <h4 class="stock-name">{{ stock.name }}</h4>
              <span class="stock-symbol">{{ stock.symbol }}</span>
            </div>
            <div class="stock-score" :class="getScoreClass(stock.score)">
              {{ stock.score }}
            </div>
          </div>

          <div class="stock-tags">
            <span v-for="tag in stock.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>

          <div class="stock-metrics">
            <div class="metric">
              <span class="metric-label">市盈率</span>
              <span class="metric-value">{{ stock.pe_ttm?.toFixed(1) || '-' }}x</span>
            </div>
            <div class="metric">
              <span class="metric-label">市净率</span>
              <span class="metric-value">{{ stock.pb?.toFixed(1) || '-' }}x</span>
            </div>
            <div class="metric">
              <span class="metric-label">ROE</span>
              <span class="metric-value">{{ stock.roe ? (stock.roe * 100).toFixed(1) : '-' }}%</span>
            </div>
            <div class="metric">
              <span class="metric-label">市值</span>
              <span class="metric-value">{{ formatMarketCap(stock.market_cap ? stock.market_cap / 100000000 : 0) }}</span>
            </div>
          </div>

          <div class="stock-price">
            <span class="price">
              {{ stock.price ? '¥' + stock.price.toFixed(2) : '-' }}
            </span>
          </div>

          <div class="card-actions">
            <button class="action-btn primary" @click="addToWatchlist(stock)">
              <el-icon><Plus /></el-icon>
              加入自选
            </button>
            <button class="action-btn" @click="viewDetail(stock)">
              详情
            </button>
          </div>

          <div class="ai-reason">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ stock.industry || '优质标的' }}，综合评分 {{ stock.score }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, Microphone, Plus, InfoFilled, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { intelligenceApi, type ScreenResult } from '@/api/intelligence'

const nlQuery = ref('')
const sortBy = ref('score')
const loading = ref(false)

const filters = ref({
  pe: [0, 30],
  pb: [0, 3],
  roe: [10, 50],
  profitGrowth: [0, 100],
  monthReturn: [0, 30],
  marketCap: [100, 5000]
})

const quickFilters = [
  { id: 1, name: '低估值蓝筹', params: { pe_max: 15, roe_min: 0.1, sort_by: 'pe', sort_order: 'asc' } },
  { id: 2, name: '高成长科技', params: { profit_growth_min: 0.3, revenue_growth_min: 0.3 } },
  { id: 3, name: '高分红', params: { industries: ['电力', '银行', '交通运输'] } },
  { id: 4, name: '小盘成长', params: { market_cap_max: 200, profit_growth_min: 0.3 } },
  { id: 5, name: '行业龙头', params: { market_cap_min: 1000 } }
]

const screenedStocks = ref<ScreenResult[]>([])
const totalCount = ref(0)
const executionTime = ref(0)

const runScreening = async () => {
  loading.value = true
  try {
    const params = {
      pe_min: filters.value.pe[0] > 0 ? filters.value.pe[0] : undefined,
      pe_max: filters.value.pe[1] < 100 ? filters.value.pe[1] : undefined,
      pb_min: filters.value.pb[0] > 0 ? filters.value.pb[0] : undefined,
      pb_max: filters.value.pb[1] < 10 ? filters.value.pb[1] : undefined,
      roe_min: filters.value.roe[0] > 0 ? filters.value.roe[0] / 100 : undefined,
      profit_growth_min: filters.value.profitGrowth[0] > 0 ? filters.value.profitGrowth[0] / 100 : undefined,
      market_cap_min: filters.value.marketCap[0] > 0 ? filters.value.marketCap[0] : undefined,
      market_cap_max: filters.value.marketCap[1] < 10000 ? filters.value.marketCap[1] : undefined,
      sort_by: sortBy.value,
      limit: 50
    }

    const res = await intelligenceApi.screenStocks(params)
    screenedStocks.value = res.data.stocks.map(s => ({
      ...s,
      score: Math.round((s.roe || 0) * 100 + (s.pe_ttm ? 100 - s.pe_ttm : 50)),
      tags: [s.industry || '股票'],
      price: s.price || 100,
      change: 0,
      changePct: 0
    }))
    totalCount.value = res.data.filtered_count
    executionTime.value = res.data.execution_time_ms
    ElMessage.success(`筛选完成，找到 ${res.data.filtered_count} 只股票`)
  } catch (e) {
    console.error(e)
    ElMessage.error('选股失败')
  } finally {
    loading.value = false
  }
}

const applyFilter = (filter: any) => {
  // 应用快捷筛选参数
  const params = filter.params
  if (params.pe_max) filters.value.pe = [0, params.pe_max]
  if (params.roe_min) filters.value.roe = [params.roe_min * 100, 50]
  if (params.market_cap_max) filters.value.marketCap = [0, params.market_cap_max]
  if (params.market_cap_min) filters.value.marketCap = [params.market_cap_min, 10000]

  runScreening()
}

const getScoreClass = (score: number) => {
  if (score >= 90) return 'excellent'
  if (score >= 80) return 'good'
  return 'normal'
}

const formatMarketCap = (cap: number) => {
  if (cap >= 10000) return (cap / 10000).toFixed(2) + '万亿'
  return cap + '亿'
}

const addToWatchlist = (stock: any) => {
  ElMessage.success(`已将 ${stock.name} 加入自选`)
}

const viewDetail = (stock: any) => {
  ElMessage.info(`查看 ${stock.name} 详情`)
}
</script>

<style scoped lang="scss">
.screener-view {
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

.ai-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(0, 217, 255, 0.15) 100%);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: var(--radius-lg);

  .ai-dot {
    width: 8px;
    height: 8px;
    background: var(--accent-purple);
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 10px var(--accent-purple);
  }

  .ai-text {
    font-size: var(--text-sm);
    font-weight: 500;
    background: linear-gradient(90deg, var(--accent-purple), var(--accent-cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

// 自然语言输入
.nl-input-section {
  margin-bottom: var(--space-6);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-xl);
  margin-bottom: var(--space-4);

  .input-icon {
    padding-left: var(--space-4);
    font-size: var(--text-xl);
    color: var(--accent-gold);
  }

  .nl-input {
    flex: 1;
    padding: var(--space-3);
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: var(--text-base);

    &::placeholder {
      color: var(--text-muted);
    }

    &:focus {
      outline: none;
    }
  }

  .search-btn {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-5);
    background: var(--gradient-gold);
    border: none;
    border-radius: var(--radius-lg);
    color: var(--bg-primary);
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-gold);
    }

    .el-icon {
      font-size: var(--text-lg);
    }
  }
}

.quick-filters {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;

  .filter-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .filter-chip {
    padding: var(--space-2) var(--space-3);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      border-color: var(--accent-gold);
      color: var(--accent-gold);
    }
  }
}

// 筛选面板
.filters-panel {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.panel-section {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);

  .section-title {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--space-4);
    padding-bottom: var(--space-3);
    border-bottom: 1px solid var(--border-primary);
  }
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.filter-item {
  label {
    display: block;
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-bottom: var(--space-2);
  }
}

// 结果区域
.results-section {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-primary);

  .results-count {
    font-size: var(--text-sm);
    color: var(--text-secondary);

    .count {
      font-family: var(--font-mono);
      font-size: var(--text-xl);
      font-weight: 700;
      color: var(--accent-gold);
    }

    .execution-time {
      font-size: var(--text-xs);
      color: var(--text-muted);
      margin-left: var(--space-2);
    }
  }
}

.stocks-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-5);
}

.stock-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  transition: all var(--transition-base);

  &:hover {
    border-color: var(--accent-gold);
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-3);
  }

  .stock-info {
    .stock-name {
      font-size: var(--text-lg);
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: var(--space-1);
    }

    .stock-symbol {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--text-muted);
    }
  }

  .stock-score {
    font-family: var(--font-mono);
    font-size: var(--text-xl);
    font-weight: 700;
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-md);

    &.excellent {
      color: var(--accent-gold);
      background: rgba(212, 175, 55, 0.15);
    }

    &.good {
      color: var(--accent-green);
      background: rgba(0, 208, 132, 0.15);
    }

    &.normal {
      color: var(--accent-cyan);
      background: rgba(0, 217, 255, 0.15);
    }
  }

  .stock-tags {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-bottom: var(--space-4);

    .tag {
      padding: 2px 8px;
      background: var(--bg-hover);
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-sm);
      font-size: 10px;
      color: var(--text-tertiary);
    }
  }

  .stock-metrics {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-3);
    margin-bottom: var(--space-4);
    padding: var(--space-3);
    background: var(--bg-hover);
    border-radius: var(--radius-md);

    .metric {
      display: flex;
      flex-direction: column;
      gap: 2px;

      .metric-label {
        font-size: 10px;
        color: var(--text-muted);
      }

      .metric-value {
        font-family: var(--font-mono);
        font-size: var(--text-sm);
        color: var(--text-secondary);
      }
    }
  }

  .stock-price {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
    margin-bottom: var(--space-4);

    .price {
      font-family: var(--font-mono);
      font-size: var(--text-xl);
      font-weight: 700;

      &.up { color: var(--accent-red); }
      &.down { color: var(--accent-green); }
    }

    .change {
      font-family: var(--font-mono);
      font-size: var(--text-sm);
      font-weight: 500;

      &.up { color: var(--accent-red); }
      &.down { color: var(--accent-green); }
    }
  }

  .card-actions {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-3);

    .action-btn {
      flex: 1;
      padding: var(--space-2);
      background: var(--bg-hover);
      border: 1px solid var(--border-primary);
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      font-size: var(--text-sm);
      cursor: pointer;
      transition: all var(--transition-fast);

      &:hover {
        border-color: var(--accent-gold);
        color: var(--accent-gold);
      }

      &.primary {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--space-1);
        background: var(--accent-gold);
        border-color: var(--accent-gold);
        color: var(--bg-primary);

        &:hover {
          box-shadow: var(--shadow-gold);
        }
      }
    }
  }

  .ai-reason {
    display: flex;
    align-items: flex-start;
    gap: var(--space-2);
    padding: var(--space-3);
    background: rgba(139, 92, 246, 0.1);
    border: 1px solid rgba(139, 92, 246, 0.2);
    border-radius: var(--radius-md);
    font-size: var(--text-xs);
    color: var(--text-secondary);

    .el-icon {
      color: var(--accent-purple);
      flex-shrink: 0;
    }
  }
}

@media (max-width: 1200px) {
  .filters-panel {
    grid-template-columns: 1fr;
  }

  .stocks-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stocks-grid {
    grid-template-columns: 1fr;
  }
}
</style>
