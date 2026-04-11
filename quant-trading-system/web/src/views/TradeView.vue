<template>
  <div class="trade-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">交易下单</h1>
        <p class="page-subtitle">快速执行交易指令</p>
      </div>
      <div class="market-status">
        <span class="status-dot"></span>
        <span class="status-text">交易中</span>
      </div>
    </div>

    <div class="trade-grid">
      <!-- 左侧：下单面板 -->
      <div class="order-panel">
        <div class="stock-selector">
          <div class="selector-label">选择标的</div>
          <div class="stock-input-wrapper">
            <input
              v-model="selectedStock.symbol"
              type="text"
              placeholder="输入股票代码"
              class="stock-input"
              @input="searchStock"
            />
            <div v-if="selectedStock.name" class="stock-name">
              {{ selectedStock.name }}
            </div>
          </div>
        </div>

        <div class="price-display">
          <div class="current-price" :class="priceChangeClass">
            <span class="price-value">{{ currentPrice.toFixed(2) }}</span>
            <span class="price-change">
              {{ priceChange >= 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}
              ({{ priceChangePct >= 0 ? '+' : '' }}{{ priceChangePct.toFixed(2) }}%)
            </span>
          </div>
          <div class="price-range">
            <span>最高: {{ highPrice.toFixed(2) }}</span>
            <span>最低: {{ lowPrice.toFixed(2) }}</span>
          </div>
        </div>

        <!-- 买卖类型切换 -->
        <div class="order-type-tabs">
          <button
            :class="['type-tab', 'buy-tab', { active: orderSide === 'buy' }]"
            @click="orderSide = 'buy'"
          >
            买入
          </button>
          <button
            :class="['type-tab', 'sell-tab', { active: orderSide === 'sell' }]"
            @click="orderSide = 'sell'"
          >
            卖出
          </button>
        </div>

        <!-- 价格输入 -->
        <div class="input-group">
          <label class="input-label">
            <span>委托价格</span>
            <el-radio-group v-model="priceType" size="small">
              <el-radio-button label="limit">限价</el-radio-button>
              <el-radio-button label="market">市价</el-radio-button>
            </el-radio-group>
          </label>
          <div class="price-input-wrapper">
            <button class="adjust-btn" @click="adjustPrice(-0.01)">−</button>
            <input
              v-model.number="orderPrice"
              type="number"
              :disabled="priceType === 'market'"
              class="price-input"
              step="0.01"
            />
            <button class="adjust-btn" @click="adjustPrice(0.01)">+</button>
          </div>
        </div>

        <!-- 数量输入 -->
        <div class="input-group">
          <label class="input-label">
            <span>委托数量</span>
            <span class="available">可用: {{ availableShares }}股</span>
          </label>
          <div class="quantity-input-wrapper">
            <button class="adjust-btn" @click="adjustQuantity(-100)">−</button>
            <input
              v-model.number="orderQuantity"
              type="number"
              class="quantity-input"
              step="100"
              min="100"
            />
            <button class="adjust-btn" @click="adjustQuantity(100)">+</button>
          </div>
          <div class="quick-quantity">
            <button
              v-for="qty in quickQuantities"
              :key="qty"
              class="quick-btn"
              @click="orderQuantity = qty"
            >
              {{ qty }}
            </button>
            <button class="quick-btn all" @click="orderQuantity = availableShares">
              全仓
            </button>
          </div>
        </div>

        <!-- 订单预览 -->
        <div class="order-preview">
          <div class="preview-row">
            <span>预估金额</span>
            <span class="preview-value">¥{{ estimatedAmount.toLocaleString() }}</span>
          </div>
          <div class="preview-row">
            <span>手续费</span>
            <span class="preview-value">¥{{ fee.toFixed(2) }}</span>
          </div>
          <div class="preview-row total">
            <span>总计</span>
            <span class="preview-value">¥{{ totalAmount.toLocaleString() }}</span>
          </div>
        </div>

        <!-- 提交按钮 -->
        <button
          :class="['submit-btn', orderSide]"
          @click="submitOrder"
        >
          {{ orderSide === 'buy' ? '买入' : '卖出' }} {{ selectedStock.symbol || '股票' }}
        </button>
      </div>

      <!-- 右侧：盘口和最近交易 -->
      <div class="market-data">
        <!-- 五档盘口 -->
        <div class="orderbook-panel">
          <div class="panel-header">
            <span class="panel-title">五档盘口</span>
            <span class="panel-symbol">{{ selectedStock.symbol || '000001.SZ' }}</span>
          </div>
          <div class="orderbook">
            <!-- 卖盘 -->
            <div class="book-side sells">
              <div
                v-for="(level, i) in asks"
                :key="`ask-${i}`"
                class="book-level"
              >
                <span class="level-label">卖{{ 5 - i }}</span>
                <span class="level-price">{{ level.price.toFixed(2) }}</span>
                <div class="level-bar">
                  <div
                    class="bar-fill sell"
                    :style="{ width: `${(level.volume / maxVolume) * 100}%` }"
                  ></div>
                  <span class="volume">{{ level.volume }}</span>
                </div>
              </div>
            </div>

            <!-- 最新价 -->
            <div class="latest-price" :class="priceChangeClass">
              <span class="price">{{ currentPrice.toFixed(2) }}</span>
              <span class="change">
                {{ priceChange >= 0 ? '▲' : '▼' }} {{ Math.abs(priceChangePct).toFixed(2) }}%
              </span>
            </div>

            <!-- 买盘 -->
            <div class="book-side buys">
              <div
                v-for="(level, i) in bids"
                :key="`bid-${i}`"
                class="book-level"
              >
                <span class="level-label">买{{ i + 1 }}</span>
                <span class="level-price">{{ level.price.toFixed(2) }}</span>
                <div class="level-bar">
                  <div
                    class="bar-fill buy"
                    :style="{ width: `${(level.volume / maxVolume) * 100}%` }"
                  ></div>
                  <span class="volume">{{ level.volume }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 最近成交 -->
        <div class="trades-panel">
          <div class="panel-header">
            <span class="panel-title">最近成交</span>
          </div>
          <div class="trades-list">
            <div
              v-for="(trade, i) in recentTrades"
              :key="i"
              class="trade-item"
            >
              <span class="trade-time">{{ trade.time }}</span>
              <span class="trade-price" :class="trade.type">
                {{ trade.price.toFixed(2) }}
              </span>
              <span class="trade-volume">{{ trade.volume }}</span>
              <span class="trade-type" :class="trade.type">
                {{ trade.type === 'buy' ? '买入' : '卖出' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

// 股票选择
const selectedStock = ref({
  symbol: '600519.SH',
  name: '贵州茅台'
})

// 价格数据
const currentPrice = ref(1725.50)
const priceChange = ref(25.50)
const priceChangePct = ref(1.50)
const highPrice = ref(1730.00)
const lowPrice = ref(1705.00)

const priceChangeClass = computed(() => {
  return priceChange.value >= 0 ? 'up' : 'down'
})

// 订单参数
const orderSide = ref<'buy' | 'sell'>('buy')
const priceType = ref<'limit' | 'market'>('limit')
const orderPrice = ref(1725.50)
const orderQuantity = ref(100)
const availableShares = ref(5000)
const quickQuantities = [100, 200, 500, 1000]

// 盘口数据
const asks = ref([
  { price: 1726.00, volume: 45 },
  { price: 1726.50, volume: 120 },
  { price: 1727.00, volume: 89 },
  { price: 1727.50, volume: 234 },
  { price: 1728.00, volume: 156 }
])

const bids = ref([
  { price: 1725.00, volume: 78 },
  { price: 1724.50, volume: 145 },
  { price: 1724.00, volume: 203 },
  { price: 1723.50, volume: 89 },
  { price: 1723.00, volume: 167 }
])

const maxVolume = computed(() => {
  const allVolumes = [...asks.value, ...bids.value].map(l => l.volume)
  return Math.max(...allVolumes)
})

// 最近成交
const recentTrades = ref([
  { time: '14:32:15', price: 1725.50, volume: 100, type: 'buy' },
  { time: '14:32:12', price: 1725.00, volume: 200, type: 'sell' },
  { time: '14:32:08', price: 1725.50, volume: 50, type: 'buy' },
  { time: '14:32:05', price: 1725.00, volume: 300, type: 'sell' },
  { time: '14:32:01', price: 1725.50, volume: 150, type: 'buy' },
  { time: '14:31:58', price: 1724.50, volume: 100, type: 'sell' },
  { time: '14:31:55', price: 1725.00, volume: 200, type: 'buy' },
  { time: '14:31:52', price: 1725.50, volume: 100, type: 'buy' }
])

// 计算
const estimatedAmount = computed(() => {
  const price = priceType.value === 'market' ? currentPrice.value : orderPrice.value
  return price * orderQuantity.value
})

const fee = computed(() => {
  return estimatedAmount.value * 0.0003 // 0.03% 手续费
})

const totalAmount = computed(() => {
  return estimatedAmount.value + fee.value
})

// 方法
const adjustPrice = (delta: number) => {
  if (priceType.value === 'market') return
  orderPrice.value = +(orderPrice.value + delta).toFixed(2)
}

const adjustQuantity = (delta: number) => {
  const newQty = orderQuantity.value + delta
  if (newQty >= 100) {
    orderQuantity.value = newQty
  }
}

const searchStock = () => {
  // 模拟搜索
  if (selectedStock.value.symbol === '000001.SZ') {
    selectedStock.value.name = '平安银行'
    currentPrice.value = 10.52
  }
}

const submitOrder = () => {
  ElMessage.success(`${orderSide.value === 'buy' ? '买入' : '卖出'}订单已提交`)
}
</script>

<style scoped lang="scss">
.trade-view {
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

.market-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);

  .status-dot {
    width: 8px;
    height: 8px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  .status-text {
    font-size: var(--text-sm);
    color: var(--accent-green);
    font-weight: 500;
  }
}

.trade-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
}

// 下单面板
.order-panel {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.stock-selector {
  margin-bottom: var(--space-5);

  .selector-label {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin-bottom: var(--space-2);
  }

  .stock-input-wrapper {
    position: relative;
  }

  .stock-input {
    width: 100%;
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: var(--font-mono);
    font-size: var(--text-lg);
    font-weight: 600;

    &::placeholder {
      color: var(--text-muted);
    }

    &:focus {
      outline: none;
      border-color: var(--accent-gold);
    }
  }

  .stock-name {
    position: absolute;
    right: var(--space-4);
    top: 50%;
    transform: translateY(-50%);
    font-size: var(--text-sm);
    color: var(--text-secondary);
  }
}

.price-display {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-5);

  .current-price {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
    margin-bottom: var(--space-2);

    &.up .price-value {
      color: var(--accent-red);
    }

    &.down .price-value {
      color: var(--accent-green);
    }

    .price-value {
      font-family: var(--font-mono);
      font-size: var(--text-3xl);
      font-weight: 700;
    }

    .price-change {
      font-family: var(--font-mono);
      font-size: var(--text-sm);
      color: var(--text-secondary);
    }
  }

  .price-range {
    display: flex;
    gap: var(--space-4);
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
}

.order-type-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.type-tab {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--border-secondary);
  }

  &.active {
    &.buy-tab {
      background: rgba(255, 71, 87, 0.15);
      border-color: var(--accent-red);
      color: var(--accent-red);
    }

    &.sell-tab {
      background: rgba(0, 208, 132, 0.15);
      border-color: var(--accent-green);
      color: var(--accent-green);
    }
  }
}

.input-group {
  margin-bottom: var(--space-5);

  .input-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-muted);

    .available {
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--text-secondary);
    }
  }
}

.price-input-wrapper,
.quantity-input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.adjust-btn {
  width: 40px;
  height: 48px;
  background: var(--bg-hover);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-lg);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--accent-gold);
    color: var(--accent-gold);
  }
}

.price-input,
.quantity-input {
  flex: 1;
  height: 48px;
  padding: 0 var(--space-4);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: 600;
  text-align: center;

  &:focus {
    outline: none;
    border-color: var(--accent-gold);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.quick-quantity {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.quick-btn {
  flex: 1;
  padding: var(--space-2);
  background: var(--bg-hover);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--accent-gold);
    color: var(--accent-gold);
  }

  &.all {
    background: rgba(212, 175, 55, 0.1);
    border-color: rgba(212, 175, 55, 0.3);
    color: var(--accent-gold);
  }
}

.order-preview {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-5);

  .preview-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-2) 0;
    font-size: var(--text-sm);
    color: var(--text-secondary);

    &.total {
      margin-top: var(--space-2);
      padding-top: var(--space-3);
      border-top: 1px solid var(--border-primary);

      .preview-value {
        font-size: var(--text-lg);
        color: var(--text-primary);
      }
    }
  }

  .preview-value {
    font-family: var(--font-mono);
    font-weight: 600;
  }
}

.submit-btn {
  width: 100%;
  padding: var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-lg);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);

  &.buy {
    background: var(--accent-red);
    color: white;

    &:hover {
      box-shadow: 0 0 20px rgba(255, 71, 87, 0.4);
    }
  }

  &.sell {
    background: var(--accent-green);
    color: var(--bg-primary);

    &:hover {
      box-shadow: 0 0 20px rgba(0, 208, 132, 0.4);
    }
  }
}

// 市场数据面板
.market-data {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.orderbook-panel,
.trades-panel {
  background: var(--gradient-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-primary);

  .panel-title {
    font-size: var(--text-base);
    font-weight: 600;
    color: var(--text-primary);
  }

  .panel-symbol {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--text-muted);
    padding: var(--space-1) var(--space-3);
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
  }
}

.orderbook {
  padding: var(--space-3);
}

.book-side {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.book-level {
  display: grid;
  grid-template-columns: 50px 80px 1fr;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }

  .level-label {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .level-price {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .level-bar {
    position: relative;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: flex-end;

    .bar-fill {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      border-radius: 2px;
      transition: width var(--transition-base);

      &.sell {
        background: rgba(255, 71, 87, 0.2);
      }

      &.buy {
        background: rgba(0, 208, 132, 0.2);
      }
    }

    .volume {
      position: relative;
      z-index: 1;
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      color: var(--text-secondary);
    }
  }
}

.latest-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-3);
  margin: var(--space-2) 0;
  border-top: 1px solid var(--border-primary);
  border-bottom: 1px solid var(--border-primary);

  &.up {
    .price {
      color: var(--accent-red);
    }
  }

  &.down {
    .price {
      color: var(--accent-green);
    }
  }

  .price {
    font-family: var(--font-mono);
    font-size: var(--text-2xl);
    font-weight: 700;
  }

  .change {
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    font-weight: 600;
  }
}

// 最近成交
.trades-list {
  max-height: 300px;
  overflow-y: auto;
  padding: var(--space-2);
}

.trade-item {
  display: grid;
  grid-template-columns: 80px 1fr 80px 60px;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);

  &:hover {
    background: var(--bg-hover);
  }

  .trade-time {
    color: var(--text-muted);
  }

  .trade-price {
    font-weight: 600;

    &.buy {
      color: var(--accent-red);
    }

    &.sell {
      color: var(--accent-green);
    }
  }

  .trade-volume {
    color: var(--text-secondary);
    text-align: right;
  }

  .trade-type {
    text-align: center;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 10px;

    &.buy {
      background: rgba(255, 71, 87, 0.15);
      color: var(--accent-red);
    }

    &.sell {
      background: rgba(0, 208, 132, 0.15);
      color: var(--accent-green);
    }
  }
}

@media (max-width: 1200px) {
  .trade-grid {
    grid-template-columns: 1fr;
  }
}
</style>
