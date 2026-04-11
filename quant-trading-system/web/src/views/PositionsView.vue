<template>
  <div class="positions-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">持仓管理</h1>
        <p class="page-subtitle">管理您的投资组合</p>
      </div>
      <div class="header-actions">
        <button class="action-btn" @click="exportPositions">
          <el-icon><Download /></el-icon>
          导出
        </button>
        <button class="action-btn primary" :loading="positionStore.loading" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </button>
      </div>
    </div>

    <!-- 持仓概览卡片 -->
    <div class="overview-cards">
      <div class="overview-card">
        <div class="card-label">持仓市值</div>
        <div class="card-value">¥{{ formatNumber(summary?.total_market_value || 0) }}</div>
        <div class="card-change" :class="getPnlClass(summary?.total_unrealized_pnl)">
          <el-icon><ArrowUp v-if="(summary?.total_unrealized_pnl || 0) >= 0" /><ArrowDown v-else /></el-icon>
          {{ formatPnl(summary?.total_unrealized_pnl_pct || 0) }}%
        </div>
      </div>
      <div class="overview-card">
        <div class="card-label">浮动盈亏</div>
        <div class="card-value" :class="getPnlClass(summary?.total_unrealized_pnl)">
          {{ formatPnl(summary?.total_unrealized_pnl || 0, true) }}
        </div>
        <div class="card-change" :class="getPnlClass(summary?.total_unrealized_pnl)">
          {{ formatPnl(summary?.total_unrealized_pnl_pct || 0) }}%
        </div>
      </div>
      <div class="overview-card">
        <div class="card-label">累计盈亏</div>
        <div class="card-value" :class="getPnlClass(summary?.total_realized_pnl)">
          {{ formatPnl(summary?.total_realized_pnl || 0, true) }}
        </div>
        <div class="card-change">已实现</div>
      </div>
      <div class="overview-card">
        <div class="card-label">持仓数量</div>
        <div class="card-value">{{ summary?.total_positions || 0 }}</div>
        <div class="card-change">只股票</div>
      </div>
    </div>

    <!-- 持仓列表 -->
    <div class="positions-table-container">
      <div class="table-header">
        <div class="table-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            :class="['tab-btn', { active: activeTab === tab.value }]"
            @click="activeTab = tab.value"
          >
            {{ tab.label }}
            <span v-if="tab.count !== undefined" class="tab-count">{{ tab.count }}</span>
          </button>
        </div>
        <div class="table-search">
          <el-input
            v-model="searchQuery"
            placeholder="搜索股票代码/名称"
            size="small"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="positionStore.loading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>

      <!-- 空状态 -->
      <div v-else-if="filteredPositions.length === 0" class="empty-state">
        <el-empty description="暂无持仓数据" />
      </div>

      <!-- 数据表格 -->
      <div v-else class="positions-table">
        <div class="table-row header">
          <div class="col-stock">股票</div>
          <div class="col-quantity">持仓</div>
          <div class="col-cost">成本价</div>
          <div class="col-price">现价</div>
          <div class="col-pnl">盈亏</div>
          <div class="col-value">市值</div>
          <div class="col-ratio">占比</div>
          <div class="col-actions">操作</div>
        </div>

        <div
          v-for="position in filteredPositions"
          :key="position.id"
          class="table-row"
        >
          <div class="col-stock">
            <div class="stock-info">
              <div class="stock-name">{{ position.symbol_name || position.symbol }}</div>
              <div class="stock-symbol">{{ position.symbol }}</div>
            </div>
          </div>
          <div class="col-quantity">
            <div class="quantity-main">{{ position.total_qty }}</div>
            <div class="quantity-sub">{{ position.available_qty }}可用</div>
          </div>
          <div class="col-cost">
            ¥{{ position.cost_price.toFixed(2) }}
          </div>
          <div class="col-price">
            <div class="price-main" :class="getPriceClass(position)">
              ¥{{ position.market_price.toFixed(2) }}
            </div>
          </div>
          <div class="col-pnl">
            <div class="pnl-main" :class="getPnlClass(position.unrealized_pnl)">
              {{ formatPnl(position.unrealized_pnl, true) }}
            </div>
            <div class="pnl-percent" :class="getPnlClass(position.unrealized_pnl)">
              {{ formatPnl(position.unrealized_pnl_pct * 100) }}%
            </div>
          </div>
          <div class="col-value">
            ¥{{ formatNumber(position.market_value) }}
          </div>
          <div class="col-ratio">
            <div class="ratio-bar">
              <div
                class="ratio-fill"
                :style="{ width: `${(position.market_value / (summary?.total_market_value || 1)) * 100}%` }"
              ></div>
            </div>
            <span class="ratio-text">{{ ((position.market_value / (summary?.total_market_value || 1)) * 100).toFixed(1) }}%</span>
          </div>
          <div class="col-actions">
            <button class="action-link" @click="buyMore(position)">加仓</button>
            <button class="action-link sell" @click="sellPosition(position)">减仓</button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="table-footer">
        <span class="total-info">共 {{ filteredPositions.length }} 条</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Download, Refresh, Search, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePositionStore, type Position } from '@/stores/position'

const positionStore = usePositionStore()
const searchQuery = ref('')
const activeTab = ref('all')

const tabs = computed(() => [
  { label: '全部持仓', value: 'all', count: positionStore.positions.length },
  { label: '盈利', value: 'profit', count: positionStore.profitablePositions.length },
  { label: '亏损', value: 'loss', count: positionStore.losingPositions.length },
])

const summary = computed(() => positionStore.summary)

const filteredPositions = computed(() => {
  let result = [...positionStore.positions]

  // 按标签过滤
  if (activeTab.value === 'profit') {
    result = result.filter(p => p.unrealized_pnl > 0)
  } else if (activeTab.value === 'loss') {
    result = result.filter(p => p.unrealized_pnl < 0)
  }

  // 按搜索关键词过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      (p.symbol_name?.toLowerCase().includes(query) || false) ||
      p.symbol.toLowerCase().includes(query)
    )
  }

  return result
})

// 加载数据
const loadData = async () => {
  await positionStore.loadPositions()
  await positionStore.loadSummary()
}

// 刷新数据
const refreshData = async () => {
  await positionStore.refreshPositions()
  ElMessage.success('数据已刷新')
}

// 导出持仓
const exportPositions = () => {
  const data = positionStore.positions.map(p => ({
    股票代码: p.symbol,
    股票名称: p.symbol_name,
    总持仓: p.total_qty,
    可用持仓: p.available_qty,
    冻结持仓: p.frozen_qty,
    成本价: p.cost_price,
    现价: p.market_price,
    市值: p.market_value,
    浮动盈亏: p.unrealized_pnl,
    盈亏比例: (p.unrealized_pnl_pct * 100).toFixed(2) + '%',
    实现盈亏: p.realized_pnl
  }))

  // 简单的CSV导出
  const headers = Object.keys(data[0] || {})
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => row[h as keyof typeof row]).join(','))
  ].join('\n')

  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `持仓数据_${new Date().toISOString().split('T')[0]}.csv`
  link.click()

  ElMessage.success('导出成功')
}

// 格式化数字
const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 格式化盈亏
const formatPnl = (value: number, withSymbol = false) => {
  const sign = value >= 0 ? '+' : ''
  const symbol = withSymbol ? (value >= 0 ? '+¥' : '-¥') : sign
  return `${symbol}${Math.abs(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// 获取盈亏样式类
const getPnlClass = (value: number | undefined) => {
  if (value === undefined) return ''
  return value >= 0 ? 'up' : 'down'
}

// 获取价格变动样式类
const getPriceClass = (position: Position) => {
  const change = position.market_price - position.cost_price
  return change >= 0 ? 'up' : 'down'
}

// 加仓
const buyMore = (position: Position) => {
  ElMessage.info(`准备加仓 ${position.symbol_name || position.symbol}`)
  // TODO: 打开交易弹窗
}

// 减仓
const sellPosition = (position: Position) => {
  ElMessage.info(`准备减仓 ${position.symbol_name || position.symbol}`)
  // TODO: 打开交易弹窗
}

// 组件挂载时加载数据
onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.positions-view {
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

  .header-actions {
    display: flex;
    gap: var(--space-3);
  }
}

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
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

  &.primary {
    background: var(--accent-gold);
    border-color: var(--accent-gold);
    color: var(--bg-primary);

    &:hover {
      box-shadow: var(--shadow-gold);
    }
  }
}

// 概览卡片
.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.overview-card {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-5);

  .card-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin-bottom: var(--space-2);
  }

  .card-value {
    font-family: var(--font-mono);
    font-size: var(--text-2xl);
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: var(--space-2);

    &.up { color: var(--accent-red); }
    &.down { color: var(--accent-green); }
  }

  .card-change {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--text-muted);

    &.up {
      color: var(--accent-red);
    }

    &.down {
      color: var(--accent-green);
    }
  }
}

// 持仓表格
.positions-table-container {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-primary);
}

.table-tabs {
  display: flex;
  gap: var(--space-2);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }

  &.active {
    background: rgba(212, 175, 55, 0.15);
    border-color: var(--accent-gold);
    color: var(--accent-gold);
  }

  .tab-count {
    padding: 2px 6px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  &.active .tab-count {
    background: rgba(212, 175, 55, 0.2);
    color: var(--accent-gold);
  }
}

.loading-state,
.empty-state {
  padding: var(--space-8);
}

.positions-table {
  .table-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr 1.5fr 1.5fr 120px 120px;
    align-items: center;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--border-primary);
    transition: background var(--transition-fast);

    &:hover:not(.header) {
      background: var(--bg-hover);
    }

    &.header {
      background: var(--bg-tertiary);
      font-size: var(--text-xs);
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
  }
}

.col-stock {
  .stock-info {
    .stock-name {
      font-size: var(--text-base);
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 2px;
    }

    .stock-symbol {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--text-muted);
    }
  }
}

.col-quantity {
  .quantity-main {
    font-family: var(--font-mono);
    font-size: var(--text-base);
    color: var(--text-primary);
  }

  .quantity-sub {
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

.col-price, .col-pnl {
  .price-main, .pnl-main {
    font-family: var(--font-mono);
    font-size: var(--text-base);
    font-weight: 600;
  }

  .price-change, .pnl-percent {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
  }
}

.col-cost, .col-value {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  color: var(--text-primary);
}

.col-ratio {
  .ratio-bar {
    height: 4px;
    background: var(--bg-hover);
    border-radius: 2px;
    margin-bottom: var(--space-1);

    .ratio-fill {
      height: 100%;
      background: var(--accent-gold);
      border-radius: 2px;
      transition: width var(--transition-base);
    }
  }

  .ratio-text {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

.col-actions {
  display: flex;
  gap: var(--space-3);

  .action-link {
    background: transparent;
    border: none;
    color: var(--accent-gold);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: color var(--transition-fast);

    &:hover {
      color: var(--accent-gold-light);
    }

    &.sell {
      color: var(--accent-green);

      &:hover {
        color: var(--accent-green-dark);
      }
    }
  }
}

// 表格底部
.table-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-primary);
  background: var(--bg-tertiary);

  .total-info {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
}

.up { color: var(--accent-red); }
.down { color: var(--accent-green); }

@media (max-width: 1200px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .positions-table .table-row {
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: var(--space-3);

    .col-ratio, .col-actions {
      display: none;
    }
  }
}

@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: 1fr;
  }
}
</style>
