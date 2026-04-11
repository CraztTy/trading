/**
 * 实时监控Store
 *
 * 管理交易监控相关的状态和WebSocket连接
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// API基础URL
const API_BASE = 'http://localhost:9000/api/v1'
const WS_URL = 'ws://localhost:9000/api/v1/monitoring/ws'

// 类型定义
export interface PortfolioData {
  total_value: number
  cash: number
  position_value: number
  daily_pnl: number
  daily_return: number
}

export interface PositionData {
  symbol: string
  name: string
  qty: number
  cost: number
  price: number
  pnl: number
  market_value: number
  alerts?: AlertItem[]
}

export interface OrderData {
  order_id: string
  symbol: string
  direction: 'BUY' | 'SELL'
  qty: number
  filled_qty: number
  price?: number
  status: string
  created_at: string
}

export interface StrategyData {
  id: string
  name: string
  type: string
  status: 'active' | 'paused' | 'stopped'
  performance: {
    return: number
    sharpe: number
  }
}

export interface RiskMetric {
  name: string
  value: string
  limit: string
  percent: number
  status: 'normal' | 'warning' | 'danger'
}

export interface AlertItem {
  type: 'warning' | 'danger' | 'info'
  message: string
}

export interface SignalData {
  id: string
  type: 'buy' | 'sell' | 'risk' | 'stop'
  symbol: string
  name: string
  strategy: string
  price: number
  time: string
}

export interface LogData {
  id: string
  time: string
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
}

export const useMonitoringStore = defineStore('monitoring', () => {
  // ============ State ============

  // WebSocket连接状态
  const wsConnected = ref(false)
  const wsConnecting = ref(false)
  const wsError = ref<string | null>(null)

  // 监控数据
  const portfolio = ref<PortfolioData>({
    total_value: 0,
    cash: 0,
    position_value: 0,
    daily_pnl: 0,
    daily_return: 0
  })

  const positions = ref<PositionData[]>([])
  const activeOrders = ref<OrderData[]>([])
  const strategies = ref<StrategyData[]>([])
  const riskMetrics = ref<RiskMetric[]>([])
  const signals = ref<SignalData[]>([])
  const logs = ref<LogData[]>([])

  // 系统状态
  const isTrading = ref(false)
  const selectedAccountId = ref<number>(1)

  // WebSocket实例
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  // ============ Getters ============

  const isConnected = computed(() => wsConnected.value)

  const positionCount = computed(() => positions.value.length)

  const activeOrderCount = computed(() => activeOrders.value.length)

  const totalPnl = computed(() => {
    return positions.value.reduce((sum, pos) => {
      return sum + (pos.pnl * pos.market_value / 100)
    }, 0)
  })

  const riskStatus = computed(() => {
    const hasDanger = riskMetrics.value.some(m => m.status === 'danger')
    const hasWarning = riskMetrics.value.some(m => m.status === 'warning')
    if (hasDanger) return { text: '告警', class: 'danger' }
    if (hasWarning) return { text: '注意', class: 'warning' }
    return { text: '正常', class: 'success' }
  })

  // ============ Actions ============

  // 连接WebSocket
  async function connect() {
    if (wsConnecting.value || wsConnected.value) return

    wsConnecting.value = true
    wsError.value = null

    try {
      ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        console.log('[Monitoring] WebSocket connected')
        wsConnected.value = true
        wsConnecting.value = false

        // 启动心跳
        startHeartbeat()

        // 订阅数据
        subscribeData()
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (err) {
          console.error('[Monitoring] Failed to parse message:', err)
        }
      }

      ws.onclose = () => {
        console.log('[Monitoring] WebSocket disconnected')
        wsConnected.value = false
        wsConnecting.value = false
        stopHeartbeat()
        scheduleReconnect()
      }

      ws.onerror = (error) => {
        console.error('[Monitoring] WebSocket error:', error)
        wsError.value = 'WebSocket连接错误'
        wsConnecting.value = false
      }
    } catch (err) {
      console.error('[Monitoring] Failed to connect:', err)
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
  }

  // 处理收到的消息
  function handleMessage(message: any) {
    switch (message.type) {
      case 'connected':
        console.log('[Monitoring]', message.message)
        break

      case 'portfolio_update':
        portfolio.value = message.data
        break

      case 'positions_update':
        positions.value = message.data
        break

      case 'orders_update':
        activeOrders.value = message.data
        break

      case 'strategies_update':
        strategies.value = message.data
        break

      case 'risk_update':
        riskMetrics.value = message.data
        break

      case 'signal':
        signals.value.unshift(message.data)
        if (signals.value.length > 50) {
          signals.value = signals.value.slice(0, 50)
        }
        break

      case 'log':
        logs.value.unshift(message.data)
        if (logs.value.length > 100) {
          logs.value = logs.value.slice(0, 100)
        }
        break

      case 'pong':
        // 心跳响应
        break

      case 'error':
        console.error('[Monitoring] Server error:', message.message)
        wsError.value = message.message
        break

      default:
        console.log('[Monitoring] Unknown message type:', message.type)
    }
  }

  // 订阅数据
  function subscribeData() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    ws.send(JSON.stringify({
      action: 'get_portfolio',
      account_id: selectedAccountId.value
    }))

    ws.send(JSON.stringify({
      action: 'get_positions',
      account_id: selectedAccountId.value
    }))

    ws.send(JSON.stringify({
      action: 'get_active_orders',
      account_id: selectedAccountId.value
    }))

    ws.send(JSON.stringify({
      action: 'get_strategies'
    }))
  }

  // 启动心跳
  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'ping' }))
      }
    }, 30000)
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

    console.log('[Monitoring] Reconnecting in 5s...')
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 5000)
  }

  // 刷新数据
  async function refreshData() {
    subscribeData()
  }

  // 切换交易状态
  function toggleTrading() {
    isTrading.value = !isTrading.value
    // 可以发送命令到后端
  }

  // 设置选中账户
  function setAccountId(accountId: number) {
    selectedAccountId.value = accountId
    refreshData()
  }

  // 添加模拟数据（用于测试）
  function addMockData() {
    portfolio.value = {
      total_value: 1245890.50,
      cash: 456890.30,
      position_value: 789000.20,
      daily_pnl: 29245.80,
      daily_return: 2.35
    }

    positions.value = [
      { symbol: '600519.SH', name: '贵州茅台', qty: 100, cost: 1650.00, price: 1685.00, pnl: 2.12, market_value: 168500 },
      { symbol: '000858.SZ', name: '五粮液', qty: 200, cost: 145.00, price: 142.30, pnl: -1.86, market_value: 28460 },
      { symbol: '000333.SZ', name: '美的集团', qty: 500, cost: 64.50, price: 65.80, pnl: 2.02, market_value: 32900 }
    ]

    activeOrders.value = [
      { order_id: 'ORD001', symbol: '600519.SH', direction: 'BUY', qty: 100, filled_qty: 0, price: 1680.00, status: 'PENDING', created_at: new Date().toISOString() }
    ]

    strategies.value = [
      { id: '1', name: '双均线突破', type: 'MACross', status: 'active', performance: { return: 15.2, sharpe: 1.5 } },
      { id: '2', name: 'MACD金叉', type: 'MACD', status: 'active', performance: { return: 8.5, sharpe: 1.2 } }
    ]

    riskMetrics.value = [
      { name: '单票仓位', value: '12.5%', limit: '20%', percent: 62.5, status: 'normal' },
      { name: '总仓位', value: '45.2%', limit: '60%', percent: 75.3, status: 'warning' },
      { name: '日亏损', value: '0.8%', limit: '2%', percent: 40, status: 'normal' }
    ]

    signals.value = [
      { id: '1', type: 'buy', symbol: '600519.SH', name: '贵州茅台', strategy: '双均线突破', price: 1685.00, time: '09:45:23' }
    ]

    logs.value = [
      { id: '1', time: '09:45:23', level: 'INFO', message: '买入信号触发: 600519.SH @ 1685.00' },
      { id: '2', time: '09:42:15', level: 'WARN', message: '卖出信号触发: 300750.SZ @ 215.50' }
    ]
  }

  return {
    // State
    wsConnected,
    wsConnecting,
    wsError,
    portfolio,
    positions,
    activeOrders,
    strategies,
    riskMetrics,
    signals,
    logs,
    isTrading,
    selectedAccountId,

    // Getters
    isConnected,
    positionCount,
    activeOrderCount,
    totalPnl,
    riskStatus,

    // Actions
    connect,
    disconnect,
    refreshData,
    toggleTrading,
    setAccountId,
    addMockData
  }
})
