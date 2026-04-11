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
        <button class="search-btn" @click="runScreening">
          <el-icon><Search /></el-icon>
          <span>智能筛选</span>
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
          找到 <span class="count">{{ screenedStocks.length }}</span> 只股票
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
              <span class="metric-value">{{ stock.pe }}x</span>
            </div>
            <div class="metric">
              <span class="metric-label">市净率</span>
              <span class="metric-value">{{ stock.pb }}x</span>
            </div>
            <div class="metric">
              <span class="metric-label">ROE</span>
              <span class="metric-value">{{ stock.roe }}%</span>
            </div>
            <div class="metric">
              <span class="metric-label">市值</span>
              <span class="metric-value">{{ formatMarketCap(stock.marketCap) }}</span>
            </div>
          </div>

          <div class="stock-price">
            <span class="price" :class="stock.change >= 0 ? 'up' : 'down'">
              ¥{{ stock.price.toFixed(2) }}
            </span>
            <span class="change" :class="stock.change >= 0 ? 'up' : 'down'">
              {{ stock.change >= 0 ? '+' : '' }}{{ stock.changePct.toFixed(2) }}%
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
            <span>{{ stock.aiReason }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search, Microphone, Plus, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const nlQuery = ref('')
const sortBy = ref('score')

const filters = ref({
  pe: [0, 30],
  pb: [0, 3],
  roe: [10, 50],
  profitGrowth: [0, 100],
  monthReturn: [0, 30],
  marketCap: [100, 5000]
})

const quickFilters = [
  { id: 1, name: '低估值蓝筹', query: '市盈率低于15的蓝筹股' },
  { id: 2, name: '高成长科技', query: '净利润增长超过30%的科技股' },
  { id: 3, name: '高分红', query: '股息率超过3%的股票' },
  { id: 4, name: '小盘成长', query: '市值小于200亿的高成长股' },
  { id: 5, name: '行业龙头', query: '各行业市值最大的龙头股' }
]

const screenedStocks = ref([
  {
    symbol: '002371.SZ',
    name: '北方华创',
    score: 92,
    tags: ['半导体', '设备龙头', '国产替代'],
    pe: 28.5,
    pb: 4.2,
    roe: 18.5,
    marketCap: 1850,
    price: 245.80,
    change: 5.2,
    changePct: 2.16,
    aiReason: '半导体设备龙头，受益于国产替代趋势，业绩持续高增长'
  },
  {
    symbol: '300760.SZ',
    name: '迈瑞医疗',
    score: 88,
    tags: ['医疗器械', '龙头', '创新'],
    pe: 32.1,
    pb: 8.5,
    roe: 28.3,
    marketCap: 3800,
    price: 312.50,
    change: 3.8,
    changePct: 1.23,
    aiReason: '医疗器械龙头，研发实力强，海外业务快速增长'
  },
  {
    symbol: '600900.SH',
    name: '长江电力',
    score: 85,
    tags: ['电力', '高分红', '稳健'],
    pe: 18.2,
    pb: 2.1,
    roe: 14.2,
    marketCap: 5200,
    price: 23.15,
    change: 0.25,
    changePct: 1.09,
    aiReason: '水电龙头，现金流稳定，股息率超过4%，适合稳健投资'
  },
  {
    symbol: '000333.SZ',
    name: '美的集团',
    score: 83,
    tags: ['家电', '龙头', '全球化'],
    pe: 12.5,
    pb: 2.8,
    roe: 22.1,
    marketCap: 4200,
    price: 59.80,
    change: 0.85,
    changePct: 1.44,
    aiReason: '家电龙头，估值合理，海外业务占比持续提升'
  },
  {
    symbol: '002594.SZ',
    name: '比亚迪',
    score: 81,
    tags: ['新能源', '汽车', '电池'],
    pe: 35.2,
    pb: 5.8,
    roe: 16.8,
    marketCap: 6800,
    price: 245.60,
    change: -2.40,
    changePct: -0.97,
    aiReason: '新能源汽车龙头，垂直一体化优势，销量持续增长'
  },
  {
    symbol: '601012.SH',
    name: '隆基绿能',
    score: 79,
    tags: ['光伏', '硅片', '新能源'],
    pe: 15.8,
    pb: 2.5,
    roe: 20.5,
    marketCap: 2100,
    price: 27.65,
    change: 1.25,
    changePct: 4.73,
    aiReason: '光伏硅片龙头，成本优势明显，受益于全球能源转型'
  }
])

const runScreening = () => {
  ElMessage.success('正在运行AI选股算法...')
}

const applyFilter = (filter: any) => {
  nlQuery.value = filter.query
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
