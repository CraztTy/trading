import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getStockList as fetchStockList,
  searchStocks as fetchSearchStocks,
  getLatestTick,
  type StockQuote
} from '@/api'
import { wsService, type TickData, type KLineData } from '@/services/websocket'

interface MarketIndex {
  code: string
  name: string
  price: number
  change: number
  changePct: number
}

export const useMarketStore = defineStore('market', () => {
  // State
  const marketIndices = ref<MarketIndex[]>([
    { code: 'SH', name: '上证指数', price: 3087.53, change: 13.81, changePct: 0.45 },
    { code: 'SZ', name: '深证成指', price: 9874.21, change: 80.24, changePct: 0.82 },
    { code: 'CY', name: '创业板指', price: 1956.32, change: -4.52, changePct: -0.23 }
  ])

  const northboundFlow = ref(124500000)
  const watchList = ref<StockQuote[]>([])
  const wsConnected = ref(false)
  const stocks = ref<StockQuote[]>([])
  const loading = ref(false)

  // WebSocket实时数据
  const latestTicks = ref<Map<string, TickData>>(new Map())
  const klineData = ref<Map<string, KLineData>>(new Map())

  // Getters
  const isMarketOpen = computed(() => {
    const hour = new Date().getHours()
    return (hour >= 9 && hour < 11) || (hour >= 13 && hour < 15)
  })

  // 获取某只股票的最新tick
  const getStockTick = (symbol: string) => {
    return latestTicks.value.get(symbol)
  }

  // Actions
  const initWebSocket = async () => {
    console.log('Initializing WebSocket connection...')

    // 监听连接状态
    wsService.onConnectionChange((connected) => {
      wsConnected.value = connected
      console.log('[MarketStore] WebSocket连接状态:', connected ? '已连接' : '已断开')
    })

    // 监听tick数据
    wsService.onTick((tick: TickData) => {
      latestTicks.value.set(tick.symbol, tick)

      // 更新自选股列表中的价格
      const watchIndex = watchList.value.findIndex(s => s.symbol === tick.symbol)
      if (watchIndex !== -1) {
        watchList.value[watchIndex] = {
          ...watchList.value[watchIndex],
          price: tick.price,
          change: tick.change || 0,
          changePct: tick.change_pct || 0
        }
      }

      // 更新股票列表中的价格
      const stockIndex = stocks.value.findIndex(s => s.symbol === tick.symbol)
      if (stockIndex !== -1) {
        stocks.value[stockIndex] = {
          ...stocks.value[stockIndex],
          price: tick.price,
          change: tick.change || 0,
          changePct: tick.change_pct || 0
        }
      }
    })

    // 监听K线数据
    wsService.onKLine((kline: KLineData) => {
      const key = `${kline.symbol}_${kline.period}`
      klineData.value.set(key, kline)
    })

    // 连接WebSocket
    await wsService.connect()
  }

  const disconnectWebSocket = () => {
    wsService.disconnect()
  }

  // 订阅标的
  const subscribeSymbols = (symbols: string[]) => {
    wsService.subscribe({
      symbols,
      dataTypes: ['tick', 'kline_1m']
    })
  }

  // 取消订阅
  const unsubscribeSymbols = (symbols: string[]) => {
    wsService.unsubscribe({ symbols })
  }

  const updateMarketData = (data: Partial<MarketIndex>) => {
    const index = marketIndices.value.findIndex(i => i.code === data.code)
    if (index !== -1) {
      marketIndices.value[index] = { ...marketIndices.value[index], ...data }
    }
  }

  const addToWatchList = (stock: StockQuote) => {
    if (!watchList.value.find(s => s.symbol === stock.symbol)) {
      watchList.value.push(stock)
      // 自动订阅
      subscribeSymbols([stock.symbol])
    }
  }

  const removeFromWatchList = (symbol: string) => {
    const index = watchList.value.findIndex(s => s.symbol === symbol)
    if (index !== -1) {
      watchList.value.splice(index, 1)
      // 取消订阅（如果其他列表中没有）
      if (!stocks.value.find(s => s.symbol === symbol)) {
        unsubscribeSymbols([symbol])
      }
    }
  }

  // API Actions
  const fetchStocks = async (limit = 100) => {
    loading.value = true
    try {
      const data = await fetchStockList(limit)
      // 转换API返回的数据格式
      stocks.value = (data as unknown as any[]).map(stock => ({
        symbol: stock.symbol,
        name: stock.name,
        price: 0,
        change: 0,
        changePct: 0,
        volume: 0,
        high: 0,
        low: 0,
        open: 0,
        preClose: 0
      }))
    } catch (error) {
      console.error('获取股票列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  const searchStock = async (keyword: string) => {
    if (!keyword.trim()) return []
    try {
      const data = await fetchSearchStocks(keyword)
      return data
    } catch (error) {
      console.error('搜索股票失败:', error)
      return []
    }
  }

  const fetchStockTick = async (symbol: string) => {
    try {
      const data = await getLatestTick(symbol)
      return data
    } catch (error) {
      console.error('获取Tick数据失败:', error)
      return null
    }
  }

  return {
    marketIndices,
    northboundFlow,
    watchList,
    wsConnected,
    stocks,
    loading,
    latestTicks,
    klineData,
    isMarketOpen,
    getStockTick,
    initWebSocket,
    disconnectWebSocket,
    subscribeSymbols,
    unsubscribeSymbols,
    updateMarketData,
    addToWatchList,
    removeFromWatchList,
    fetchStocks,
    searchStock,
    fetchStockTick
  }
})