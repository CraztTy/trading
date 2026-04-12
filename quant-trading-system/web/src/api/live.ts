/**
 * 实盘监控API
 */
import apiClient from './client'

export type TradeMode = 'auto' | 'manual' | 'simulate' | 'pause'

export interface SignalEvent {
  id: string
  timestamp: string
  strategy_id: string
  strategy_name: string
  symbol: string
  signal_type: 'buy' | 'sell'
  price: number
  volume: number
  confidence: number
  reason: string
  status: 'pending' | 'confirmed' | 'ignored' | 'executed'
}

export interface SignalResponse {
  success: boolean
  order_id?: string
  message: string
}

export interface PerformanceStats {
  signals: {
    total_signals: number
    published_signals: number
    deduplicated_signals: number
    throttled_signals: number
  }
  mode: TradeMode
}

export const liveApi = {
  // 获取实盘状态
  getStatus: () => apiClient.get('/live/status'),

  // 启动实盘
  start: (config: { symbols?: string[]; strategies?: string[]; auto_trade?: boolean }) =>
    apiClient.post('/live/start', config),

  // 停止实盘
  stop: () => apiClient.post('/live/stop'),

  // 设置交易模式
  setMode: (mode: TradeMode) => apiClient.post('/live/mode', { mode }),

  // 获取信号历史
  getSignals: (params?: {
    strategy_id?: string
    symbol?: string
    status?: string
    limit?: number
  }) => apiClient.get('/live/signals', { params }),

  // 获取待确认信号
  getPendingSignals: () => apiClient.get('/live/signals/pending'),

  // 确认信号
  confirmSignal: (signalId: string) =>
    apiClient.post(`/live/signals/${signalId}/confirm`),

  // 忽略信号
  ignoreSignal: (signalId: string) =>
    apiClient.post(`/live/signals/${signalId}/ignore`),

  // 获取模拟交易记录
  getSimulatedTrades: () => apiClient.get('/live/simulated-trades'),

  // 获取绩效
  getPerformance: () => apiClient.get('/live/performance')
}

export default liveApi
