/**
 * 风控管理 API
 */
import apiClient from './client'

export interface RiskStatus {
  status: 'safe' | 'warning' | 'danger'
  score: number
  active_rules: number
  pending_alerts: number
}

export interface RiskRule {
  code: string
  name: string
  type: string
  level: string
  enabled: boolean
  stats: {
    total_checks: number
    failures: number
  }
}

export interface RiskAlert {
  id: number
  level: 'WARNING' | 'CRITICAL'
  title: string
  message: string
  timestamp: string
  acknowledged: boolean
}

export interface PositionRisk {
  symbol: string
  quantity: number
  market_value: number
  weight: number
  unrealized_pnl_pct: number
  stop_loss: number | null
  take_profit: number | null
  risk_level: 'low' | 'medium' | 'high'
}

export interface RiskReport {
  timestamp: string
  overall_status: string
  risk_score: number
  position_summary: {
    current_capital: number
    total_position_value: number
    total_position_weight: number
    available_cash: number
    position_count: number
  }
  active_stop_losses: Record<string, {
    stop_price: string
    type: string
    is_active: boolean
  }>
  active_take_profits: Record<string, {
    target_price: string
    type: string
    is_active: boolean
  }>
  recent_alerts: RiskAlert[]
}

export interface RuleConfig {
  enabled: boolean
  config: Record<string, any>
}

export const riskApi = {
  // 获取风控状态
  getStatus: () => apiClient.get<RiskStatus>('/risk/status'),

  // 获取风控报告
  getReport: () => apiClient.get<RiskReport>('/risk/report'),

  // 获取所有规则
  getRules: () => apiClient.get<RiskRule[]>('/risk/rules'),

  // 启用/禁用规则
  toggleRule: (code: string) =>
    apiClient.post(`/risk/rules/${code}/toggle`),

  // 更新规则配置
  updateRule: (code: string, config: RuleConfig) =>
    apiClient.put(`/risk/rules/${code}`, config),

  // 获取持仓风险
  getPositionRisks: () => apiClient.get<PositionRisk[]>('/risk/positions'),

  // 获取预警列表
  getAlerts: (params?: {
    level?: string
    acknowledged?: boolean
    limit?: number
  }) => apiClient.get<RiskAlert[]>('/risk/alerts', { params }),

  // 确认预警
  acknowledgeAlert: (alertId: number) =>
    apiClient.post(`/risk/alerts/${alertId}/ack`),

  // 清空已确认预警
  clearAcknowledgedAlerts: () =>
    apiClient.post('/risk/alerts/clear'),

  // 紧急清仓
  emergencyClose: (reason: string, confirm: boolean = true) =>
    apiClient.post('/risk/emergency-close', { reason, confirm }),

  // 更新止损价
  updateStopLoss: (symbol: string, price: number) =>
    apiClient.post(`/risk/stop-loss/${symbol}`, null, { params: { price } }),

  // 更新止盈价
  updateTakeProfit: (symbol: string, price: number) =>
    apiClient.post(`/risk/take-profit/${symbol}`, null, { params: { price } })
}

export default riskApi
