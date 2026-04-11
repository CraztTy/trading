<template>
  <div class="orderbook">
    <div class="orderbook-col">
      <div class="orderbook-header">
        <span>买价</span>
        <span>数量</span>
        <span>档位</span>
      </div>
      <div
        v-for="(bid, index) in bids"
        :key="index"
        class="orderbook-row bid"
      >
        <div class="orderbook-bar" :style="{ width: bid.width + '%' }"></div>
        <span class="price">{{ bid.price.toFixed(2) }}</span>
        <span>{{ bid.volume }}</span>
        <span style="color: var(--text-muted)">买{{ index + 1 }}</span>
      </div>
    </div>

    <div class="orderbook-col">
      <div class="orderbook-header">
        <span>卖价</span>
        <span>数量</span>
        <span>档位</span>
      </div>
      <div
        v-for="(ask, index) in asks"
        :key="index"
        class="orderbook-row ask"
      >
        <div class="orderbook-bar" :style="{ width: ask.width + '%' }"></div>
        <span class="price">{{ ask.price.toFixed(2) }}</span>
        <span>{{ ask.volume }}</span>
        <span style="color: var(--text-muted)">卖{{ index + 1 }}</span>
      </div>
    </div>
  </div>

  <div class="trade-actions">
    <el-button class="btn-trade btn-buy" @click="handleBuy">买入</el-button>
    <el-button class="btn-trade btn-sell" @click="handleSell">卖出</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface Props {
  symbol: string
}

const props = defineProps<Props>()

const bids = ref([
  { price: 1724.99, volume: 23, width: 60 },
  { price: 1724.88, volume: 18, width: 45 },
  { price: 1724.77, volume: 12, width: 30 },
  { price: 1724.66, volume: 10, width: 25 },
  { price: 1724.55, volume: 6, width: 15 }
])

const asks = ref([
  { price: 1725.01, volume: 21, width: 55 },
  { price: 1725.12, volume: 15, width: 40 },
  { price: 1725.23, volume: 14, width: 35 },
  { price: 1725.34, volume: 8, width: 20 },
  { price: 1725.45, volume: 4, width: 10 }
])

const handleBuy = () => {
  ElMessage.success(`买入 ${props.symbol}`)
}

const handleSell = () => {
  ElMessage.warning(`卖出 ${props.symbol}`)
}
</script>

<style scoped lang="scss">
.orderbook {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 20px;
}

.orderbook-col {
  background: var(--bg-card);
}

.orderbook-header {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  padding: 10px;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-color);
}

.orderbook-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  padding: 8px 10px;
  font-size: 12px;
  position: relative;
  cursor: pointer;

  &:hover {
    background: var(--bg-hover);
  }

  &.bid .price {
    color: var(--accent-green);
  }

  &.ask .price {
    color: var(--accent-red);
  }
}

.orderbook-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  opacity: 0.15;

  .bid & {
    right: 0;
    background: var(--accent-green);
  }

  .ask & {
    left: 0;
    background: var(--accent-red);
  }
}

.trade-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.btn-trade {
  padding: 14px 24px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 1px;

  &.btn-buy {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(0, 255, 136, 0.05) 100%);
    color: var(--accent-green);
    border: 1px solid rgba(0, 255, 136, 0.3);

    &:hover {
      background: var(--accent-green);
      color: var(--bg-primary);
    }
  }

  &.btn-sell {
    background: linear-gradient(135deg, rgba(255, 71, 87, 0.15) 0%, rgba(255, 71, 87, 0.05) 100%);
    color: var(--accent-red);
    border: 1px solid rgba(255, 71, 87, 0.3);

    &:hover {
      background: var(--accent-red);
      color: var(--bg-primary);
    }
  }
}
</style>