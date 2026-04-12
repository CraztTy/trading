/**
 * 回测API客户端
 */
import apiClient from './client'

export interface CreateBacktestRequest {
  symbols: string[]
  start_date: string
  end_date: string
  strategy_id: string
  initial_capital: number
  params?: Record<string, any>
}

export interface BacktestTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  symbols: string[]
  start_date: string
  end_date: string
  strategy_id: string
  initial_capital: number
  created_at: string
  completed_at?: string
  error_message?: string
}

export interface BacktestSummary {
  total_return: number
  total_return_pct: string
  total_trades: number
  win_rate: string
  max_drawdown: string
  sharpe_ratio: number
  annualized_return: string
}

export interface Trade {
  date: string
  symbol: string
  direction: 'buy' | 'sell'
  price: number
  volume: number
  amount: number
}

export interface DailyValue {
  date: string
  value: number
  cash: number
  positions_value: number
}

export interface MonthlyReturn {
  month: string
  return_pct: number
}

export interface BacktestResult {
  summary: BacktestSummary
  trades: Trade[]
  daily_values: DailyValue[]
  monthly_returns: MonthlyReturn[]
}

export interface StrategyParam {
  name: string
  label: string
  type: 'number' | 'select' | 'string' | 'boolean'
  min?: number
  max?: number
  default?: any
  options?: { label: string; value: any }[]
}

export interface Strategy {
  id: string
  name: string
  description: string
  params: StrategyParam[]
}

// 创建回测任务
export const createBacktestTask = (data: CreateBacktestRequest) => {
  return apiClient.post('/backtest/', data)
}

// 获取任务详情
export const getBacktestTask = (taskId: string) => {
  return apiClient.get(`/backtest/${taskId}`)
}

// 获取回测结果
export const getBacktestResults = (taskId: string) => {
  return apiClient.get(`/backtest/${taskId}/results`)
}

// 获取任务列表
export const listBacktestTasks = (params?: {
  status?: string
  limit?: number
  offset?: number
}) => {
  return apiClient.get('/backtest/', { params })
}

// 删除任务
export const deleteBacktestTask = (taskId: string) => {
  return apiClient.delete(`/backtest/${taskId}`)
}

// 获取策略列表
export const getStrategies = () => {
  return apiClient.get('/backtest/strategies')
}

// 获取策略详情
export const getStrategy = (strategyId: string) => {
  return apiClient.get(`/backtest/strategies/${strategyId}`)
}
