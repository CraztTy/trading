<template>
  <div class="kline-chart">
    <div class="chart-header">
      <div class="header-left">
        <span class="chart-icon">◫</span>
        <h3 class="chart-title">{{ symbol || '请选择标的' }}</h3>
        <span v-if="currentTick" class="price-info" :class="priceChangeClass">
          {{ formatPrice(currentTick.price) }}
          <span class="change">{{ formatChange(currentTick.change) }}</span>
        </span>
      </div>
      <div class="time-periods">
        <button
          v-for="p in periods"
          :key="p.value"
          class="period-btn"
          :class="{ active: period === p.value }"
          @click="changePeriod(p.value)"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div ref="chartContainer" class="chart-container"></div>

    <div class="chart-footer">
      <div class="legend">
        <span>MA5: {{ ma5 }}</span>
        <span>MA10: {{ ma10 }}</span>
        <span>MA20: {{ ma20 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData, type Time } from 'lightweight-charts'
import { useMarketStore } from '@/stores/market'

interface Props {
  symbol: string
}

const props = defineProps<Props>()
const marketStore = useMarketStore()

// Chart refs
const chartContainer = ref<HTMLElement | null>(null)
let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null

// State
const period = ref('1d')
const periods = [
  { label: '1分', value: '1m' },
  { label: '5分', value: '5m' },
  { label: '15分', value: '15m' },
  { label: '30分', value: '30m' },
  { label: '1时', value: '1h' },
  { label: '日线', value: '1d' },
]

// Computed
const currentTick = computed(() => {
  if (!props.symbol) return null
  return marketStore.tickCache.get(props.symbol)
})

const priceChangeClass = computed(() => {
  const tick = currentTick.value
  if (!tick || !tick.change) return 'neutral'
  return tick.change > 0 ? 'positive' : tick.change < 0 ? 'negative' : 'neutral'
})

const ma5 = ref('--')
const ma10 = ref('--')
const ma20 = ref('--')

// Initialize chart
function initChart() {
  if (!chartContainer.value) return

  chart = createChart(chartContainer.value, {
    layout: {
      background: { color: 'transparent' },
      textColor: '#94a3b8',
    },
    grid: {
      vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
      horzLines: { color: 'rgba(148, 163, 184, 0.1)' },
    },
    crosshair: {
      mode: 1,
      vertLine: {
        color: '#00f0ff',
        labelBackgroundColor: '#00f0ff',
      },
      horzLine: {
        color: '#00f0ff',
        labelBackgroundColor: '#00f0ff',
      },
    },
    rightPriceScale: {
      borderColor: 'rgba(148, 163, 184, 0.2)',
    },
    timeScale: {
      borderColor: 'rgba(148, 163, 184, 0.2)',
      timeVisible: true,
    },
  })

  // Candlestick series
  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#00f0ff',
    downColor: '#ff00aa',
    borderUpColor: '#00f0ff',
    borderDownColor: '#ff00aa',
    wickUpColor: '#00f0ff',
    wickDownColor: '#ff00aa',
  })

  // Volume series
  volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: {
      type: 'volume',
    },
    priceScaleId: '',
    scaleMargins: {
      top: 0.8,
      bottom: 0,
    },
  })

  // Handle resize
  const resizeObserver = new ResizeObserver(() => {
    if (chart && chartContainer.value) {
      chart.applyOptions({
        width: chartContainer.value.clientWidth,
        height: chartContainer.value.clientHeight,
      })
    }
  })
  resizeObserver.observe(chartContainer.value)
}

// Load mock data (will be replaced with real data)
function loadMockData() {
  if (!candlestickSeries || !volumeSeries) return

  const data: CandlestickData[] = []
  const volumeData: any[] = []
  let time = new Date('2024-01-01').getTime() / 1000
  let price = 100

  for (let i = 0; i < 100; i++) {
    const open = price
    const close = open + (Math.random() - 0.5) * 5
    const high = Math.max(open, close) + Math.random() * 2
    const low = Math.min(open, close) - Math.random() * 2
    const volume = Math.floor(Math.random() * 10000) + 1000

    data.push({
      time: time as Time,
      open,
      high,
      low,
      close,
    })

    volumeData.push({
      time: time as Time,
      value: volume,
      color: close >= open ? 'rgba(0, 240, 255, 0.5)' : 'rgba(255, 0, 170, 0.5)',
    })

    price = close
    time += 86400 // 1 day
  }

  candlestickSeries.setData(data)
  volumeSeries.setData(volumeData)

  // Fit content
  chart?.timeScale().fitContent()
}

// Update with real-time tick
function updateWithTick(tick: any) {
  if (!candlestickSeries || !tick) return

  const lastData = candlestickSeries.data()[candlestickSeries.data().length - 1]
  if (!lastData) return

  const time = Math.floor(new Date().getTime() / 1000)

  // Update last candle
  candlestickSeries.update({
    time: lastData.time,
    open: lastData.open,
    high: Math.max(lastData.high, tick.price),
    low: Math.min(lastData.low, tick.price),
    close: tick.price,
  })
}

// Change period
function changePeriod(newPeriod: string) {
  period.value = newPeriod
  // TODO: Load data for new period from backend
  loadMockData()
}

// Format helpers
function formatPrice(price: number | undefined): string {
  if (price === undefined) return '--'
  return price.toFixed(2)
}

function formatChange(change: number | undefined): string {
  if (change === undefined) return '--'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toFixed(2)}`
}

// Watch for symbol changes
watch(() => props.symbol, (newSymbol) => {
  if (newSymbol) {
    // Subscribe to symbol
    // marketStore.subscribeSymbols([newSymbol])
    loadMockData()
  }
})

// Watch for tick updates
watch(() => currentTick.value, (tick) => {
  if (tick) {
    updateWithTick(tick)
  }
}, { deep: true })

onMounted(() => {
  initChart()
  loadMockData()

  // Subscribe to current symbol
  if (props.symbol) {
    // marketStore.subscribeSymbols([props.symbol])
  }
})

onUnmounted(() => {
  if (chart) {
    chart.remove()
    chart = null
  }
})
</script>

<style scoped>
.kline-chart {
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, var(--bg-layer) 0%, var(--bg-surface) 100%);
  border: 1px solid var(--border-subtle);
  position: relative;
}

.kline-chart::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--neon-cyan), transparent);
  opacity: 0.5;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chart-icon {
  font-size: 1rem;
  color: var(--neon-cyan);
}

.chart-title {
  font-family: var(--font-display);
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.price-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
}

.price-info.positive {
  color: var(--neon-cyan);
}

.price-info.negative {
  color: var(--neon-magenta);
}

.price-info.neutral {
  color: var(--text-secondary);
}

.price-info .change {
  font-size: 0.75rem;
  opacity: 0.8;
}

.time-periods {
  display: flex;
  gap: 0.25rem;
}

.period-btn {
  padding: 0.375rem 0.75rem;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.3s;
}

.period-btn:hover {
  color: var(--text-primary);
  border-color: var(--border-medium);
}

.period-btn.active {
  background: var(--neon-cyan-dim);
  border-color: var(--neon-cyan);
  color: var(--neon-cyan);
}

.chart-container {
  flex: 1;
  min-height: 400px;
  position: relative;
}

.chart-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.legend {
  display: flex;
  gap: 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-tertiary);
}
</style>
