<template>
  <div class="market-ticker">
    <div class="ticker-header">
      <span class="ticker-title">实时行情</span>
      <div class="ticker-status">
        <span
          class="status-dot"
          :class="{ connected: marketStore.wsConnected, disconnected: !marketStore.wsConnected }"
        ></span>
        <span class="status-text">
          {{ marketStore.wsConnected ? '已连接' : marketStore.wsConnecting ? '连接中...' : '已断开' }}
        </span>
      </div>
    </div>

    <div class="ticker-list">
      <div
        v-for="item in marketStore.watchList"
        :key="item.symbol"
        class="ticker-item"
        
      >
        <div class="ticker-info">
          <span class="ticker-symbol">{{ item.symbol }}</span>
          <span class="ticker-name">{{ item.name }}</span>
        </div>

        <div v-if="item.tick" class="ticker-data">
          <span
            class="ticker-price"
            :class="getPriceClass(item.tick)"
          >
            {{ formatPrice(item.tick.price) }}
          </span>

          <span
            class="ticker-change"
            :class="getPriceClass(item.tick)"
          >
            {{ formatChange(item.tick.change) }}
            ({{ formatChangePct(item.tick.change_pct) }})
          </span>
        </div>

        <div v-else-if="item.isLoading" class="ticker-loading">
          <span class="loading-text">加载中...</span>
        </div>

        <div v-else class="ticker-no-data">
          <span>暂无数据</span>
        </div>

        <!-- 成交量 -->
        <div v-if="item.tick" class="ticker-volume">
          <span>量: {{ formatVolume(item.tick.volume) }}</span>
        </div>

        <!-- 删除按钮 -->
        <button class="remove-btn" @click="removeItem(item.symbol)">
          ×
        </button>
      </div>
    </div>

    <!-- 添加自选股 -->
    <div class="add-stock">
      <input
        v-model="newSymbol"
        type="text"
        placeholder="输入股票代码 (如: 000001.SZ)"
        @keyup.enter="addStock"
      />
      <button class="cyber-btn" @click="addStock" :disabled="!newSymbol">
        添加
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMarketStore } from '@/stores/market'

interface TickData {
  symbol: string
  price?: number
  change?: number
  change_pct?: number
  pre_close?: number
  volume?: number
}

const marketStore = useMarketStore()
const newSymbol = ref('')

// 记录最近更新的标的，用于动画效果

// 监听tick更新
onMounted(() => {
  // 连接WebSocket
  marketStore.connect()
})

onUnmounted(() => {
  // 断开WebSocket
  marketStore.disconnect()
})

// 获取价格样式类
function getPriceClass(tick: TickData): string {
  if (!tick.change) return 'neutral'
  return tick.change > 0 ? 'positive' : tick.change < 0 ? 'negative' : 'neutral'
}

// 格式化价格
function formatPrice(price: number | undefined): string {
  if (price === undefined) return '--'
  return price.toFixed(2)
}

// 格式化涨跌额
function formatChange(change: number | undefined): string {
  if (change === undefined) return '--'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toFixed(2)}`
}

// 格式化涨跌幅
function formatChangePct(pct: number | undefined): string {
  if (pct === undefined) return '--'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

// 格式化成交量
function formatVolume(volume: number | undefined): string {
  if (volume === undefined) return '--'
  if (volume >= 10000) {
    return (volume / 10000).toFixed(1) + '万'
  }
  return volume.toString()
}

// 添加自选股
function addStock() {
  if (!newSymbol.value) return

  const symbol = newSymbol.value.trim().toUpperCase()
  const name = symbol // TODO: 从API获取股票名称

  marketStore.addToWatchList(symbol, name)
  newSymbol.value = ''
}

// 删除自选股
function removeItem(symbol: string) {
  marketStore.removeFromWatchList(symbol)
}
</script>

<style scoped>
.market-ticker {
  background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%);
  border: 1px solid var(--border-subtle);
  padding: 1rem;
}

.market-ticker::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--neon-cyan), transparent);
  opacity: 0.5;
}

.ticker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-subtle);
}

.ticker-title {
  font-family: var(--font-display);
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.ticker-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  transition: all 0.3s;
}

.status-dot.connected {
  background: var(--neon-cyan);
  box-shadow: 0 0 10px var(--neon-cyan);
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.disconnected {
  background: var(--text-muted);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-tertiary);
}

.ticker-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.ticker-item {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  transition: all 0.3s;
  position: relative;
}

.ticker-item:hover {
  border-color: var(--border-medium);
}

.ticker-item.updating {
  border-left: 2px solid var(--neon-cyan);
  background: var(--neon-cyan-dim);
}

.ticker-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.ticker-symbol {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.ticker-name {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.ticker-data {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.ticker-price {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.ticker-change {
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.ticker-change.positive,
.ticker-price.positive {
  color: var(--signal-buy);
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

.ticker-change.negative,
.ticker-price.negative {
  color: var(--signal-sell);
  text-shadow: 0 0 10px rgba(255, 0, 170, 0.3);
}

.ticker-change.neutral,
.ticker-price.neutral {
  color: var(--text-secondary);
}

.ticker-volume {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--text-muted);
  text-align: right;
}

.ticker-loading,
.ticker-no-data {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.remove-btn {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1rem;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
}

.ticker-item:hover .remove-btn {
  opacity: 1;
}

.remove-btn:hover {
  color: var(--neon-magenta);
}

/* 添加自选股 */
.add-stock {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-subtle);
}

.add-stock input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--bg-deep);
  border: 1px solid var(--border-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.add-stock input::placeholder {
  color: var(--text-muted);
}

.add-stock input:focus {
  outline: none;
  border-color: var(--neon-cyan);
}

.cyber-btn {
  padding: 0.5rem 1rem;
  background: var(--neon-cyan-dim);
  border: 1px solid var(--neon-cyan);
  color: var(--neon-cyan);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.3s;
}

.cyber-btn:hover:not(:disabled) {
  background: var(--neon-cyan);
  color: var(--bg-void);
}

.cyber-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 滚动条 */
.ticker-list::-webkit-scrollbar {
  width: 4px;
}

.ticker-list::-webkit-scrollbar-track {
  background: var(--bg-deep);
}

.ticker-list::-webkit-scrollbar-thumb {
  background: var(--border-medium);
}
</style>
