import apiClient from './client'

export interface Strategy {
  id: number
  strategy_id: string
  name: string
  description: string
  strategy_type: string
  status: 'draft' | 'active' | 'paused' | 'stopped' | 'error'
  parameters_schema: Record<string, any>
  default_parameters: Record<string, any>
  symbols: string[]
  total_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
  win_rate?: number
  total_trades: number
  current_version: number
  created_at: string
  updated_at: string
}

export interface CreateStrategyRequest {
  name: string
  code: string
  description?: string
  strategy_type?: string
  parameters_schema?: Record<string, any>
  default_parameters?: Record<string, any>
  symbols?: string[]
}

export interface StrategyListResponse {
  items: Strategy[]
  total: number
  page: number
  page_size: number
}

export interface BacktestConfig {
  start_date?: string
  end_date?: string
  symbols?: string[]
  initial_capital?: number
  parameters?: Record<string, any>
}

export const strategyApi = {
  getStrategies: (params?: { status?: string; limit?: number; offset?: number }) =>
    apiClient.get<StrategyListResponse>('/strategies/', { params }),

  getStrategy: (id: string) =>
    apiClient.get<Strategy>(`/strategies/${id}`),

  createStrategy: (data: CreateStrategyRequest) =>
    apiClient.post<Strategy>('/strategies/', data),

  updateStrategy: (id: string, data: Partial<CreateStrategyRequest>) =>
    apiClient.put<Strategy>(`/strategies/${id}`, data),

  deleteStrategy: (id: string) =>
    apiClient.delete(`/strategies/${id}`),

  startStrategy: (id: string) =>
    apiClient.post(`/strategies/${id}/start`),

  stopStrategy: (id: string) =>
    apiClient.post(`/strategies/${id}/stop`),

  pauseStrategy: (id: string) =>
    apiClient.post(`/strategies/${id}/pause`),

  runBacktest: (id: string, config?: BacktestConfig) =>
    apiClient.post(`/strategies/${id}/backtest`, config),
}
