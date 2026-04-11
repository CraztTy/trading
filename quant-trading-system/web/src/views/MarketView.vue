<template>
  <div class="market-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">市场行情</h1>
        <p class="page-subtitle">实时查看A股行情数据</p>
      </div>
      <div class="header-actions">
        <el-button @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索股票代码或名称"
        clearable
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button @click="handleSearch">搜索</el-button>
        </template>
      </el-input>
    </div>

    <!-- 股票列表 -->
    <div class="stock-table-container">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <el-icon><Warning /></el-icon>
        <p>{{ error }}</p>
        <el-button @click="fetchStockList">重试</el-button>
      </div>

      <table v-else class="stock-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>最新价</th>
            <th>涨跌幅</th>
            <th>涨跌额</th>
            <th>成交量</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stock in displayStocks" :key="stock.symbol">
            <td class="symbol">{{ stock.symbol }}</td>
            <td class="name">{{ stock.name }}</td>
            <td :class="['price', stock.change >= 0 ? 'up' : 'down']">
              {{ stock.price.toFixed(2) }}
            </td>
            <td :class="['change', stock.change >= 0 ? 'up' : 'down']">
              {{ stock.change >= 0 ? '+' : '' }}{{ stock.changePct.toFixed(2) }}%
            </td>
            <td :class="['change', stock.change >= 0 ? 'up' : 'down']">
              {{ stock.change >= 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}
            </td>
            <td class="volume">{{ formatVolume(stock.volume) }}</td>
            <td>
              <button class="action-btn" @click="addToWatch(stock)">
                加入自选
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Refresh, Warning } from '@element-plus/icons-vue'
import { useMarketStore } from '@/stores/market'
import { searchStocks } from '@/api'
import { ElMessage } from 'element-plus'

const marketStore = useMarketStore()
const searchQuery = ref('')
const loading = ref(false)
const error = ref('')

// 本地股票数据（带模拟价格）
const stocks = ref([
  { symbol: '000001.SZ', name: '平安银行', price: 10.52, change: 0.04, changePct: 0.38, volume: 1520000 },
  { symbol: '600519.SH', name: '贵州茅台', price: 1725.00, change: 21.25, changePct: 1.25, volume: 25000 },
  { symbol: '300750.SZ', name: '宁德时代', price: 200.50, change: -2.30, changePct: -1.13, volume: 120000 },
  { symbol: '000858.SZ', name: '五粮液', price: 154.80, change: 3.20, changePct: 2.11, volume: 85000 },
  { symbol: '002594.SZ', name: '比亚迪', price: 245.60, change: -2.40, changePct: -0.97, volume: 95000 },
  { symbol: '601012.SH', name: '隆基绿能', price: 27.65, change: 1.25, changePct: 4.73, volume: 450000 },
  { symbol: '002371.SZ', name: '北方华创', price: 245.80, change: 5.20, changePct: 2.16, volume: 32000 },
  { symbol: '300760.SZ', name: '迈瑞医疗', price: 312.50, change: 3.80, changePct: 1.23, volume: 18000 },
  { symbol: '600900.SH', name: '长江电力', price: 23.15, change: 0.25, changePct: 1.09, volume: 520000 },
  { symbol: '000333.SZ', name: '美的集团', price: 59.80, change: 0.85, changePct: 1.44, volume: 380000 }
])

const displayStocks = computed(() => {
  return stocks.value
})

const formatVolume = (volume: number) => {
  if (volume >= 10000) {
    return (volume / 10000).toFixed(2) + '万'
  }
  return volume.toString()
}

// 从API获取股票列表
const fetchStockList = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await searchStocks('', 100)
    if (data && Array.isArray(data)) {
      // 合并API数据和本地模拟价格
      stocks.value = data.map((stock: any) => ({
        ...stock,
        price: Math.random() * 200 + 10,
        change: (Math.random() - 0.5) * 10,
        changePct: (Math.random() - 0.5) * 5,
        volume: Math.floor(Math.random() * 1000000)
      }))
    }
  } catch (err: any) {
    error.value = err.message || '获取股票列表失败'
    console.error('获取股票列表失败:', err)
  } finally {
    loading.value = false
  }
}

// 搜索股票
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    await fetchStockList()
    return
  }

  loading.value = true
  try {
    const data = await searchStocks(searchQuery.value, 20)
    if (data && Array.isArray(data)) {
      stocks.value = data.map((stock: any) => ({
        ...stock,
        price: Math.random() * 200 + 10,
        change: (Math.random() - 0.5) * 10,
        changePct: (Math.random() - 0.5) * 5,
        volume: Math.floor(Math.random() * 1000000)
      }))
    }
  } catch (err: any) {
    ElMessage.error(err.message || '搜索失败')
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  fetchStockList()
}

const addToWatch = (stock: any) => {
  marketStore.addToWatchList(stock)
  ElMessage.success(`已将 ${stock.name} 加入自选`)
}

onMounted(() => {
  fetchStockList()
})
</script>

<style scoped lang="scss">
.market-view {
  max-width: 1200px;
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

.search-bar {
  margin-bottom: var(--space-5);

  :deep(.el-input__wrapper) {
    background: var(--bg-tertiary);
    box-shadow: 0 0 0 1px var(--border-primary);
  }

  :deep(.el-input__inner) {
    color: var(--text-primary);
  }
}

.stock-table-container {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  color: var(--text-muted);

  .el-icon {
    font-size: var(--text-3xl);
    margin-bottom: var(--space-4);
  }
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-primary);
  border-top-color: var(--accent-gold);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--space-4);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.stock-table {
  width: 100%;
  border-collapse: collapse;

  th {
    background: var(--bg-tertiary);
    padding: var(--space-4);
    text-align: left;
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border-primary);
  }

  td {
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-primary);
    font-size: var(--text-sm);
  }

  tr:hover td {
    background: var(--bg-hover);
  }

  .symbol {
    font-family: var(--font-mono);
    color: var(--text-secondary);
  }

  .name {
    font-weight: 500;
    color: var(--text-primary);
  }

  .price {
    font-family: var(--font-mono);
    font-weight: 600;
  }

  .change {
    font-family: var(--font-mono);

    &.up {
      color: var(--accent-red);
    }

    &.down {
      color: var(--accent-green);
    }
  }

  .volume {
    font-family: var(--font-mono);
    color: var(--text-secondary);
  }

  .action-btn {
    padding: var(--space-2) var(--space-3);
    background: var(--bg-hover);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    font-size: var(--text-xs);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      border-color: var(--accent-gold);
      color: var(--accent-gold);
    }
  }
}

.up {
  color: var(--accent-red);
}

.down {
  color: var(--accent-green);
}
</style>
