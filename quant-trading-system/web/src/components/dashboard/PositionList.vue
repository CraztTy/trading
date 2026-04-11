<template>
  <div class="position-list">
    <div
      v-for="pos in positions"
      :key="pos.symbol"
      class="position-item"
    >
      <div class="position-info">
        <span class="position-symbol">{{ pos.symbol }}</span>
        <span class="position-name">{{ pos.name }}</span>
        <span class="position-qty">持仓: {{ pos.quantity }}股</span>
      </div>
      <div class="position-pnl">
        <div :class="['pnl-value', pos.unrealizedPnl >= 0 ? 'positive' : 'negative']">
          {{ pos.unrealizedPnl >= 0 ? '+' : '' }}¥{{ formatNumber(pos.unrealizedPnl) }}
        </div>
        <div class="pnl-percent">
          {{ pos.unrealizedPnlPct >= 0 ? '+' : '' }}{{ (pos.unrealizedPnlPct * 100).toFixed(2) }}%
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Position {
  symbol: string
  name: string
  quantity: number
  avgCost: number
  currentPrice: number
  marketValue: number
  unrealizedPnl: number
  unrealizedPnlPct: number
}

interface Props {
  positions: Position[]
}

defineProps<Props>()

const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}
</script>

<style scoped lang="scss">
.position-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.position-item {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
  cursor: pointer;

  &:hover {
    border-color: var(--border-glow);
    transform: translateX(4px);
  }
}

.position-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.position-symbol {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.position-name {
  font-size: 12px;
  color: var(--text-muted);
}

.position-qty {
  font-size: 12px;
  color: var(--text-secondary);
}

.position-pnl {
  text-align: right;
}

.pnl-value {
  font-size: 16px;
  font-weight: 600;
  font-family: var(--font-mono);

  &.positive {
    color: var(--accent-green);
  }

  &.negative {
    color: var(--accent-red);
  }
}

.pnl-percent {
  font-size: 12px;
  color: var(--text-muted);
}
</style>