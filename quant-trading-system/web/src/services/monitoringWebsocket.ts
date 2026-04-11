/**
 * 监控WebSocket服务
 * 管理订单、持仓、策略等实时数据推送
 */
import { ElMessage } from 'element-plus'

// 消息类型
export interface MonitoringMessage {
  type: string
  data?: any
  timestamp?: string
  message?: string
}

// 订单更新数据
export interface OrderUpdate {
  order_id: string
  symbol: string
  direction: string
  qty: number
  price?: number
  status: string
  filled_qty: number
  remaining_qty: number
  filled_avg_price: number
  updated_at: string
}

// 持仓更新数据
export interface PositionUpdate {
  id: number
  symbol: string
  symbol_name?: string
  total_qty: number
  market_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
}

// 风险告警
export interface RiskAlert {
  level: 'info' | 'warning' | 'critical'
  message: string
  details?: Record<string, any>
}

// 回调函数类型
type MessageHandler = (message: MonitoringMessage) => void
type OrderUpdateHandler = (order: OrderUpdate) => void
type PositionUpdateHandler = (position: PositionUpdate) => void
type RiskAlertHandler = (alert: RiskAlert) => void
type ConnectionHandler = (connected: boolean) => void

class MonitoringWebSocketService {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectDelay: number = 3000
  private heartbeatInterval: number = 30000
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 回调函数集合
  private messageHandlers: Set<MessageHandler> = new Set()
  private orderUpdateHandlers: Set<OrderUpdateHandler> = new Set()
  private positionUpdateHandlers: Set<PositionUpdateHandler> = new Set()
  private riskAlertHandlers: Set<RiskAlertHandler> = new Set()
  private connectionHandlers: Set<ConnectionHandler> = new Set()

  // 连接状态
  private _connected: boolean = false
  private subscribedAccounts: Set<number> = new Set()

  constructor() {
    const baseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:9000/ws'
    this.url = `${baseUrl}/monitoring/ws`
  }

  /**
   * 连接WebSocket
   */
  connect(): Promise<boolean> {
    return new Promise((resolve) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve(true)
        return
      }

      try {
        // 从localStorage获取token
        const token = localStorage.getItem('access_token')
        if (!token) {
          console.error('[MonitoringWS] 未找到认证token')
          resolve(false)
          return
        }

        // 带token连接
        this.ws = new WebSocket(`${this.url}?token=${token}`)

        this.ws.onopen = () => {
          console.log('[MonitoringWS] 连接成功')
          this._connected = true
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.notifyConnectionHandlers(true)

          // 重新订阅之前的账户
          this.subscribedAccounts.forEach(accountId => {
            this.subscribeAccount(accountId)
          })

          resolve(true)
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.ws.onclose = (event) => {
          console.log('[MonitoringWS] 连接关闭', event.code, event.reason)
          this._connected = false
          this.stopHeartbeat()
          this.notifyConnectionHandlers(false)

          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }

          resolve(false)
        }

        this.ws.onerror = (error) => {
          console.error('[MonitoringWS] 连接错误:', error)
          this._connected = false
          resolve(false)
        }
      } catch (error) {
        console.error('[MonitoringWS] 连接失败:', error)
        resolve(false)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.stopHeartbeat()
    this.clearReconnectTimer()

    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close(1000, '主动关闭')
      }
      this.ws = null
    }

    this._connected = false
    this.subscribedAccounts.clear()
    this.notifyConnectionHandlers(false)
  }

  // ============ 订阅管理 ============

  /**
   * 订阅账户监控
   */
  subscribeAccount(accountId: number): void {
    this.send({
      action: 'subscribe_account',
      account_id: accountId
    })
    this.subscribedAccounts.add(accountId)
  }

  /**
   * 取消订阅账户
   */
  unsubscribeAccount(accountId: number): void {
    this.send({
      action: 'unsubscribe_account',
      account_id: accountId
    })
    this.subscribedAccounts.delete(accountId)
  }

  /**
   * 请求组合信息
   */
  requestPortfolio(accountId: number): void {
    this.send({
      action: 'get_portfolio',
      account_id: accountId
    })
  }

  /**
   * 请求持仓数据
   */
  requestPositions(accountId: number): void {
    this.send({
      action: 'get_positions',
      account_id: accountId
    })
  }

  /**
   * 请求活跃订单
   */
  requestActiveOrders(accountId: number): void {
    this.send({
      action: 'get_active_orders',
      account_id: accountId
    })
  }

  /**
   * 请求策略状态
   */
  requestStrategies(): void {
    this.send({ action: 'get_strategies' })
  }

  // ============ 消息处理 ============

  private send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  private handleMessage(data: string): void {
    try {
      const message: MonitoringMessage = JSON.parse(data)

      // 通知所有消息处理器
      this.messageHandlers.forEach(handler => {
        try { handler(message) } catch (e) {}
      })

      // 根据类型分发
      switch (message.type) {
        case 'connected':
          console.log('[MonitoringWS]', message.message)
          break

        case 'order_update':
          this.orderUpdateHandlers.forEach(handler => {
            try { handler(message.data) } catch (e) {}
          })
          break

        case 'position_update':
          this.positionUpdateHandlers.forEach(handler => {
            try { handler(message.data) } catch (e) {}
          })
          break

        case 'risk_alert':
          const alert = message.data as RiskAlert
          if (alert.level === 'critical') {
            ElMessage.error(`风险告警: ${alert.message}`)
          } else if (alert.level === 'warning') {
            ElMessage.warning(`风险提醒: ${alert.message}`)
          }
          this.riskAlertHandlers.forEach(handler => {
            try { handler(alert) } catch (e) {}
          })
          break

        case 'portfolio_update':
        case 'positions_update':
        case 'orders_update':
        case 'strategies_update':
          // 这些数据更新通过messageHandlers处理
          break

        case 'error':
          console.error('[MonitoringWS] 错误:', message.message)
          break

        case 'pong':
          break

        default:
          console.log('[MonitoringWS] 未知消息类型:', message.type)
      }
    } catch (error) {
      console.error('[MonitoringWS] 消息解析错误:', error)
    }
  }

  // ============ 心跳与重连 ============

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({ action: 'ping' })
      }
    }, this.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect(): void {
    this.clearReconnectTimer()
    this.reconnectAttempts++

    console.log(`[MonitoringWS] ${this.reconnectDelay}ms后尝试第${this.reconnectAttempts}次重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, this.reconnectDelay)

    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000)
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  // ============ 事件监听 ============

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onOrderUpdate(handler: OrderUpdateHandler): () => void {
    this.orderUpdateHandlers.add(handler)
    return () => this.orderUpdateHandlers.delete(handler)
  }

  onPositionUpdate(handler: PositionUpdateHandler): () => void {
    this.positionUpdateHandlers.add(handler)
    return () => this.positionUpdateHandlers.delete(handler)
  }

  onRiskAlert(handler: RiskAlertHandler): () => void {
    this.riskAlertHandlers.add(handler)
    return () => this.riskAlertHandlers.delete(handler)
  }

  onConnectionChange(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    handler(this._connected)
    return () => this.connectionHandlers.delete(handler)
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try { handler(connected) } catch (e) {}
    })
  }

  // ============ Getters ============

  get isConnected(): boolean {
    return this._connected && this.ws?.readyState === WebSocket.OPEN
  }
}

// 单例导出
export const monitoringWsService = new MonitoringWebSocketService()
export default monitoringWsService
