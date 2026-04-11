/**
 * 三省架构状态管理 (Pinia)
 *
 * 管理三省六部核心架构的前端状态：
 * - 太子院：数据校验统计
 * - 中书省：策略信号
 * - 门下省：风控审核
 * - 尚书省：订单执行
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { wsService, type TickData, type KLineData } from '@/services/websocket'

// 信号类型
export interface Signal {
  id: string
  type: 'buy' | 'sell'
  symbol: string
  price: number
  volume: number
  timestamp: string
  strategyId?: string
  reason?: string
  confidence?: number
}

// 风控审核结果
export interface AuditResult {
  approved: boolean
  signalId: string
  rejectedBy?: string
  rejectReason?: string
  auditTime: string
}

// 订单
export interface Order {
  id: string
  symbol: string
  direction: 'buy' | 'sell'
  price: number
  volume: number
  status: 'pending' | 'frozen' | 'submitted' | 'filled' | 'rejected' | 'cancelled'
  createdAt: string
  filledQty?: number
  filledPrice?: number
}

// 成交
export interface Trade {
  id: string
  orderId: string
  symbol: string
  direction: 'buy' | 'sell'
  price: number
  volume: number
  amount: number
  commission: number
  timestamp: string
}

// 持仓
export interface Position {
  symbol: string
  name?: string
  totalQty: number
  availableQty: number
  avgCost: number
  marketPrice: number
  marketValue: number
  unrealizedPnl: number
  unrealizedPnlPct: number
}

export const useShengStore = defineStore('sheng', () => {
  // ============ State ============

  // 太子院 - 数据校验统计
  const crownPrinceStats = ref({
    totalReceived: 0,
    valid: 0,
    invalid: 0,
    dispatched: 0
  })

  // 中书省 - 策略信号
  const signals = ref<Signal[]>([])
  const signalStats = ref({
    generated: 0,
    deduplicated: 0,
    activeStrategies: 0
  })

  // 门下省 - 风控审核
  const auditResults = ref<AuditResult[]>([])
  const menxiaStats = ref({
    totalAudits: 0,
    approved: 0,
    rejected: 0,
    circuitBreakerActive: false,
    circuitBreakerReason: ''
  })

  // 尚书省 - 订单执行
  const orders = ref<Order[]>([])
  const trades = ref<Trade[]>([])
  const shangshuStats = ref({
    submitted: 0,
    executed: 0,
    rejected: 0
  })

  // 持仓
  const positions = ref<Position[]>([])

  // 实时行情
  const latestTicks = ref<Map<string, TickData>>(new Map())
  const klineData = ref<Map<string, KLineData>>(new Map())

  // WebSocket连接状态
  const wsConnected = ref(false)

  // ============ Getters ============

  const totalPositionValue = computed(() => {
    return positions.value.reduce((sum, p) => sum + p.marketValue, 0)
  })

  const totalUnrealizedPnl = computed(() => {
    return positions.value.reduce((sum, p) => sum + p.unrealizedPnl, 0)
  })

  const pendingOrders = computed(() => {
    return orders.value.filter(o => ['pending', 'frozen', 'submitted'].includes(o.status))
  })

  const todayTrades = computed(() => {
    const today = new Date().toISOString().split('T')[0]
    return trades.value.filter(t => t.timestamp.startsWith(today))
  })

  // ============ Actions ============

  // 初始化WebSocket
  const initWebSocket = async () => {
    // 监听连接状态
    wsService.onConnectionChange((connected) => {
      wsConnected.value = connected
      if (connected) {
        ElMessage.success('行情连接已建立')
      } else {
        ElMessage.warning('行情连接已断开')
      }
    })

    // 监听Tick数据
    wsService.onTick((tick) => {
      latestTicks.value.set(tick.symbol, tick)

      // 更新持仓市价
      updatePositionPrice(tick.symbol, tick.price)
    })

    // 监听K线数据
    wsService.onKLine((kline) => {
      const key = `${kline.symbol}_${kline.period}`
      klineData.value.set(key, kline)
    })

    // 连接
    await wsService.connect()
  }

  // 断开WebSocket
  const disconnectWebSocket = () => {
    wsService.disconnect()
  }

  // 订阅标的
  const subscribeSymbols = (symbols: string[]) => {
    wsService.subscribe({ symbols, dataTypes: ['tick', 'kline_1m'] })
  }

  // 取消订阅
  const unsubscribeSymbols = (symbols: string[]) => {
    wsService.unsubscribe({ symbols })
  }

  // 更新持仓价格
  const updatePositionPrice = (symbol: string, price: number) => {
    const position = positions.value.find(p => p.symbol === symbol)
    if (position) {
      position.marketPrice = price
      position.marketValue = price * position.totalQty
      position.unrealizedPnl = position.marketValue - (position.avgCost * position.totalQty)
      position.unrealizedPnlPct = position.avgCost > 0
        ? (position.unrealizedPnl / (position.avgCost * position.totalQty)) * 100
        : 0
    }
  }

  // 添加信号
  const addSignal = (signal: Signal) => {
    signals.value.unshift(signal)
    // 只保留最近100条
    if (signals.value.length > 100) {
      signals.value = signals.value.slice(0, 100)
    }
    signalStats.value.generated++
  }

  // 添加审核结果
  const addAuditResult = (result: AuditResult) => {
    auditResults.value.unshift(result)
    if (auditResults.value.length > 100) {
      auditResults.value = auditResults.value.slice(0, 100)
    }

    menxiaStats.value.totalAudits++
    if (result.approved) {
      menxiaStats.value.approved++
    } else {
      menxiaStats.value.rejected++
    }

    // 更新信号状态
    const signal = signals.value.find(s => s.id === result.signalId)
    if (signal) {
      // 可以在这里标记信号状态
    }
  }

  // 添加订单
  const addOrder = (order: Order) => {
    orders.value.unshift(order)
    if (orders.value.length > 100) {
      orders.value = orders.value.slice(0, 100)
    }
    shangshuStats.value.submitted++
  }

  // 更新订单状态
  const updateOrderStatus = (orderId: string, status: Order['status'], filledInfo?: { qty: number, price: number }) => {
    const order = orders.value.find(o => o.id === orderId)
    if (order) {
      order.status = status
      if (filledInfo) {
        order.filledQty = filledInfo.qty
        order.filledPrice = filledInfo.price
      }
    }
  }

  // 添加成交
  const addTrade = (trade: Trade) => {
    trades.value.unshift(trade)
    if (trades.value.length > 100) {
      trades.value = trades.value.slice(0, 100)
    }
    shangshuStats.value.executed++

    // 更新订单状态
    updateOrderStatus(trade.orderId, 'filled', { qty: trade.volume, price: trade.price })

    // 更新持仓
    updatePositionAfterTrade(trade)
  }

  // 交易后更新持仓
  const updatePositionAfterTrade = (trade: Trade) => {
    const position = positions.value.find(p => p.symbol === trade.symbol)

    if (trade.direction === 'buy') {
      if (position) {
        // 加仓
        const oldCost = position.avgCost * position.totalQty
        const newCost = trade.price * trade.volume
        position.totalQty += trade.volume
        position.availableQty += trade.volume
        position.avgCost = (oldCost + newCost) / position.totalQty
      } else {
        // 新开仓
        positions.value.push({
          symbol: trade.symbol,
          totalQty: trade.volume,
          availableQty: trade.volume,
          avgCost: trade.price,
          marketPrice: trade.price,
          marketValue: trade.amount,
          unrealizedPnl: 0,
          unrealizedPnlPct: 0
        })
      }
    } else {
      // 卖出
      if (position) {
        position.totalQty -= trade.volume
        position.availableQty -= trade.volume

        if (position.totalQty <= 0) {
          // 全部平仓
          const idx = positions.value.indexOf(position)
          positions.value.splice(idx, 1)
        } else {
          // 更新成本
          position.avgCost = position.avgCost // 卖出不改变成本价
          position.marketValue = position.marketPrice * position.totalQty
        }
      }
    }
  }

  // 设置熔断状态
  const setCircuitBreaker = (active: boolean, reason?: string) => {
    menxiaStats.value.circuitBreakerActive = active
    menxiaStats.value.circuitBreakerReason = reason || ''

    if (active) {
      ElMessage.error(`风控熔断: ${reason}`)
    } else {
      ElMessage.success('风控熔断已解除')
    }
  }

  // 更新太子院统计
  const updateCrownPrinceStats = (stats: typeof crownPrinceStats.value) => {
    crownPrinceStats.value = stats
  }

  // 清空数据
  const clearData = () => {
    signals.value = []
    auditResults.value = []
    orders.value = []
    trades.value = []
    positions.value = []
  }

  return {
    // State
    crownPrinceStats,
    signals,
    signalStats,
    auditResults,
    menxiaStats,
    orders,
    trades,
    shangshuStats,
    positions,
    latestTicks,
    klineData,
    wsConnected,

    // Getters
    totalPositionValue,
    totalUnrealizedPnl,
    pendingOrders,
    todayTrades,

    // Actions
    initWebSocket,
    disconnectWebSocket,
    subscribeSymbols,
    unsubscribeSymbols,
    addSignal,
    addAuditResult,
    addOrder,
    updateOrderStatus,
    addTrade,
    setCircuitBreaker,
    updateCrownPrinceStats,
    clearData
  }
})