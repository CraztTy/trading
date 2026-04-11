/**
 * WebSocket服务
 * 管理行情数据实时推送连接
 */
import { ElMessage } from 'element-plus'

// WebSocket消息类型
export interface WSMessage {
  type: string
  data?: any
  message?: string
}

// Tick数据
export interface TickData {
  symbol: string
  timestamp: string
  price: number
  volume: number
  bid_price?: number
  bid_volume?: number
  ask_price?: number
  ask_volume?: number
  change?: number
  change_pct?: number
}

// K线数据
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

// 订阅配置
export interface SubscribeConfig {
  symbols: string[]
  dataTypes?: string[]
}

// 回调函数类型
type MessageHandler = (message: WSMessage) => void
type TickHandler = (tick: TickData) => void
type KLineHandler = (kline: KLineData) => void
type ConnectionHandler = (connected: boolean) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectDelay: number = 3000
  private heartbeatInterval: number = 30000
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 订阅状态
  private subscribedSymbols: Set<string> = new Set()
  private subscribedDataTypes: string[] = ['tick']

  // 回调函数集合
  private messageHandlers: Set<MessageHandler> = new Set()
  private tickHandlers: Set<TickHandler> = new Set()
  private klineHandlers: Set<KLineHandler> = new Set()
  private connectionHandlers: Set<ConnectionHandler> = new Set()

  // 连接状态
  private _connected: boolean = false

  constructor() {
    // 从环境变量获取WebSocket地址
    const baseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:9000/ws'
    this.url = `${baseUrl}/market/ws`
  }

  // ============ 连接管理 ============

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
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('[WebSocket] 连接成功')
          this._connected = true
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.notifyConnectionHandlers(true)

          // 重新订阅之前的标的
          if (this.subscribedSymbols.size > 0) {
            this.subscribe({
              symbols: Array.from(this.subscribedSymbols),
              dataTypes: this.subscribedDataTypes
            })
          }

          resolve(true)
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.ws.onclose = (event) => {
          console.log('[WebSocket] 连接关闭', event.code, event.reason)
          this._connected = false
          this.stopHeartbeat()
          this.notifyConnectionHandlers(false)

          // 非主动关闭，尝试重连
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }

          resolve(false)
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocket] 连接错误:', error)
          this._connected = false
          resolve(false)
        }
      } catch (error) {
        console.error('[WebSocket] 连接失败:', error)
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
      // 发送取消订阅
      this.unsubscribe({ symbols: Array.from(this.subscribedSymbols) })

      // 关闭连接
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close(1000, '主动关闭')
      }
      this.ws = null
    }

    this._connected = false
    this.subscribedSymbols.clear()
    this.notifyConnectionHandlers(false)
  }

  /**
   * 重新连接
   */
  async reconnect(): Promise<boolean> {
    this.disconnect()
    await new Promise(resolve => setTimeout(resolve, 1000))
    return this.connect()
  }

  // ============ 订阅管理 ============

  /**
   * 订阅标的
   */
  subscribe(config: SubscribeConfig): void {
    const { symbols, dataTypes = ['tick'] } = config

    if (!this.isConnected) {
      console.warn('[WebSocket] 未连接，无法订阅')
      // 保存订阅配置，连接后自动订阅
      symbols.forEach(s => this.subscribedSymbols.add(s))
      this.subscribedDataTypes = dataTypes
      return
    }

    this.send({
      action: 'subscribe',
      symbols,
      data_types: dataTypes
    })

    // 记录订阅状态
    symbols.forEach(s => this.subscribedSymbols.add(s))
    this.subscribedDataTypes = dataTypes
  }

  /**
   * 取消订阅
   */
  unsubscribe(config: { symbols: string[] }): void {
    const { symbols } = config

    if (!this.isConnected) return

    this.send({
      action: 'unsubscribe',
      symbols
    })

    // 移除订阅记录
    symbols.forEach(s => this.subscribedSymbols.delete(s))
  }

  /**
   * 发送ping心跳
   */
  ping(): void {
    this.send({ action: 'ping' })
  }

  // ============ 消息处理 ============

  private send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  private handleMessage(data: string): void {
    try {
      const message: WSMessage = JSON.parse(data)

      // 通知所有消息处理器
      this.messageHandlers.forEach(handler => {
        try {
          handler(message)
        } catch (e) {
          console.error('[WebSocket] 消息处理器错误:', e)
        }
      })

      // 根据类型分发
      switch (message.type) {
        case 'tick':
          this.handleTickMessage(message.data)
          break
        case 'kline_1m':
        case 'kline_5m':
        case 'kline_15m':
        case 'kline_30m':
        case 'kline_1h':
        case 'kline_1d':
          this.handleKLineMessage(message.data)
          break
        case 'connected':
          console.log('[WebSocket]', message.message)
          break
        case 'subscribed':
          console.log('[WebSocket] 订阅成功:', message.data)
          break
        case 'error':
          console.error('[WebSocket] 错误:', message.message)
          ElMessage.error(message.message || 'WebSocket错误')
          break
        case 'pong':
          // 心跳响应，无需处理
          break
        default:
          console.log('[WebSocket] 未知消息类型:', message.type)
      }
    } catch (error) {
      console.error('[WebSocket] 消息解析错误:', error)
    }
  }

  private handleTickMessage(data: TickData): void {
    this.tickHandlers.forEach(handler => {
      try {
        handler(data)
      } catch (e) {
        console.error('[WebSocket] Tick处理器错误:', e)
      }
    })
  }

  private handleKLineMessage(data: KLineData): void {
    this.klineHandlers.forEach(handler => {
      try {
        handler(data)
      } catch (e) {
        console.error('[WebSocket] K线处理器错误:', e)
      }
    })
  }

  // ============ 心跳与重连 ============

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.ping()
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

    console.log(`[WebSocket] ${this.reconnectDelay}ms后尝试第${this.reconnectAttempts}次重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, this.reconnectDelay)

    // 指数退避
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

  onTick(handler: TickHandler): () => void {
    this.tickHandlers.add(handler)
    return () => this.tickHandlers.delete(handler)
  }

  onKLine(handler: KLineHandler): () => void {
    this.klineHandlers.add(handler)
    return () => this.klineHandlers.delete(handler)
  }

  onConnectionChange(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    // 立即通知当前状态
    handler(this._connected)
    return () => this.connectionHandlers.delete(handler)
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected)
      } catch (e) {
        console.error('[WebSocket] 连接状态处理器错误:', e)
      }
    })
  }

  // ============ Getters ============

  get isConnected(): boolean {
    return this._connected && this.ws?.readyState === WebSocket.OPEN
  }

  get subscribedCount(): number {
    return this.subscribedSymbols.size
  }

  get subscribedList(): string[] {
    return Array.from(this.subscribedSymbols)
  }
}

// 单例导出
export const wsService = new WebSocketService()
export default wsService
