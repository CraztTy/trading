/**
 * 行情数据Store
 *
 * 管理实时行情数据、自选股、WebSocket连接
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 数据类型定义
export interface TickData {
  symbol: string
  timestamp: string
  price: number
  volume: number
  bid_price?: number
  bid_volume?: number
  ask_price?: number
  ask_volume?: number
  open?: number
  high?: number
  low?: number
  pre_close?: number
  change?: number
  change_pct?: number
}

export interface KLineData {
  symbol: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  period: string
}

export interface WatchListItem {
  symbol: string
  name: string
  tick?: TickData
  isLoading: boolean
}

export const useMarketStore = defineStore('market', () => {
  // ============ State ============

  // WebSocket连接
  const wsConnected = ref(false)
  const wsConnecting = ref(false)
  const wsError = ref<string | null>(null)

  // 实时数据缓存
  const tickCache = ref<Map<string, TickData>>(new Map())
  const klineCache = ref<Map<string, KLineData[]>>(new Map())

  // 自选股列表
  const watchList = ref<WatchListItem[]>([
    { symbol: '000001.SZ', name: '平安银行', isLoading: true },
    { symbol: '600519.SH', name: '贵州茅台', isLoading: true },
    { symbol: '300750.SZ', name: '宁德时代', isLoading: true },
  ])

  // 活跃标的（当前订阅的）
  const activeSymbols = ref<Set<string>>(new Set())

  // WebSocket实例
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  // ============ Getters ============

  // 获取指定标的的最新tick
  const getTick = computed(() => (symbol: string) => {
    return tickCache.value.get(symbol)
  })

  // 获取涨跌幅颜色
  const getChangeColor = computed(() => (change: number) => {
    if (change > 0) return 'positive'
    if (change < 0) return 'negative'
    return 'neutral'
  })

  // 计算涨跌幅
  const calculateChange = computed(() => (tick: TickData) => {
    if (tick.pre_close && tick.price) {
      const change = tick.price - tick.pre_close
      const changePct = (change / tick.pre_close) * 100
      return { change, changePct }
    }
    return { change: 0, changePct: 0 }
  })

  // ============ Actions ============

  // 连接WebSocket
  async function connect() {
    if (wsConnecting.value || wsConnected.value) return

    wsConnecting.value = true
    wsError.value = null

    try {
      const wsUrl = `ws://${window.location.hostname}:9000/api/v1/market/ws`
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Market] WebSocket connected')
        wsConnected.value = true
        wsConnecting.value = false
        wsError.value = null

        // 启动心跳
        startHeartbeat()

        // 订阅自选股
        subscribeSymbols(watchList.value.map(item => item.symbol))
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (err) {
          console.error('[Market] Failed to parse message:', err)
        }
      }

      ws.onclose = () => {
        console.log('[Market] WebSocket disconnected')
        wsConnected.value = false
        wsConnecting.value = false
        stopHeartbeat()

        // 自动重连
        scheduleReconnect()
      }

      ws.onerror = (error) => {
        console.error('[Market] WebSocket error:', error)
        wsError.value = 'WebSocket连接错误'
        wsConnecting.value = false
      }
    } catch (err) {
      console.error('[Market] Failed to connect:', err)
      wsError.value = '连接失败'
      wsConnecting.value = false
      scheduleReconnect()
    }
  }

  // 断开连接
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopHeartbeat()

    if (ws) {
      ws.close()
      ws = null
    }

    wsConnected.value = false
    activeSymbols.value.clear()
  }

  // 处理收到的消息
  function handleMessage(message: any) {
    switch (message.type) {
      case 'connected':
        console.log('[Market]', message.message)
        break

      case 'tick':
        handleTick(message.data)
        break

      case 'kline_1m':
      case 'kline_5m':
      case 'kline_15m':
      case 'kline_1h':
      case 'kline_1d':
        handleKLine(message.data, message.type.replace('kline_', ''))
        break

      case 'subscribed':
        console.log('[Market] Subscribed:', message.symbols)
        message.symbols.forEach((symbol: string) => {
          activeSymbols.value.add(symbol)
        })
        break

      case 'unsubscribed':
        console.log('[Market] Unsubscribed:', message.symbols)
        message.symbols.forEach((symbol: string) => {
          activeSymbols.value.delete(symbol)
        })
        break

      case 'pong':
        // 心跳响应
        break

      case 'error':
        console.error('[Market] Server error:', message.message)
        wsError.value = message.message
        break

      default:
        console.log('[Market] Unknown message type:', message.type)
    }
  }

  // 处理Tick数据
  function handleTick(data: TickData) {
    // 计算涨跌幅
    if (data.pre_close && data.price) {
      data.change = data.price - data.pre_close
      data.change_pct = (data.change / data.pre_close) * 100
    }

    tickCache.value.set(data.symbol, data)

    // 更新自选股列表中的数据
    const watchItem = watchList.value.find(item => item.symbol === data.symbol)
    if (watchItem) {
      watchItem.tick = data
      watchItem.isLoading = false
    }
  }

  // 处理K线数据
  function handleKLine(data: KLineData, period: string) {
    const key = `${data.symbol}_${period}`
    const existing = klineCache.value.get(key) || []

    // 检查是否是新K线
    const lastKLine = existing[existing.length - 1]
    if (lastKLine && lastKLine.timestamp === data.timestamp) {
      // 更新当前K线
      existing[existing.length - 1] = data
    } else {
      // 添加新K线
      existing.push(data)
      // 限制缓存大小
      if (existing.length > 1000) {
        existing.shift()
      }
    }

    klineCache.value.set(key, existing)
  }

  // 订阅标的
  function subscribeSymbols(symbols: string[]) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    const message = {
      action: 'subscribe',
      symbols: symbols,
      data_types: ['tick'],
    }

    ws.send(JSON.stringify(message))
  }

  // 取消订阅
  function unsubscribeSymbols(symbols: string[]) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    const message = {
      action: 'unsubscribe',
      symbols: symbols,
    }

    ws.send(JSON.stringify(message))
  }

  // 添加自选股
  function addToWatchList(symbol: string, name: string) {
    // 检查是否已存在
    if (watchList.value.some(item => item.symbol === symbol)) {
      return
    }

    watchList.value.push({
      symbol,
      name,
      isLoading: true,
    })

    // 如果已连接，立即订阅
    if (wsConnected.value) {
      subscribeSymbols([symbol])
    }
  }

  // 删除自选股
  function removeFromWatchList(symbol: string) {
    const index = watchList.value.findIndex(item => item.symbol === symbol)
    if (index > -1) {
      watchList.value.splice(index, 1)

      // 取消订阅
      if (wsConnected.value) {
        unsubscribeSymbols([symbol])
      }
    }
  }

  // 启动心跳
  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'ping' }))
      }
    }, 30000) // 30秒心跳
  }

  // 停止心跳
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // 计划重连
  function scheduleReconnect() {
    if (reconnectTimer) return

    console.log('[Market] Reconnecting in 5s...')
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 5000)
  }

  return {
    // State
    wsConnected,
    wsConnecting,
    wsError,
    tickCache,
    klineCache,
    watchList,
    activeSymbols,

    // Getters
    getTick,
    getChangeColor,
    calculateChange,

    // Actions
    connect,
    disconnect,
    subscribeSymbols,
    unsubscribeSymbols,
    addToWatchList,
    removeFromWatchList,
  }
})
