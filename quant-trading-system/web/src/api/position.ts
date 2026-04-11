/**
 * 持仓相关API
 */
import apiClient from './client'

export interface Position {
  id: number
  account_id: number
  strategy_id?: number
  symbol: string
  symbol_name?: string
  total_qty: number
  available_qty: number
  frozen_qty: number
  cost_price: number
  cost_amount: number
  market_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  realized_pnl: number
  weight: number
  opened_at?: string
  updated_at: string
}

export interface PositionSummary {
  total_positions: number
  total_market_value: number
  total_cost: number
  total_unrealized_pnl: number
  total_unrealized_pnl_pct: number
  total_realized_pnl: number
}

/**
 * 获取持仓列表
 */
export const getPositions = (params?: {
  account_id?: number
  symbol?: string
  min_qty?: number
}): Promise<Position[]> => {
  return apiClient.get('/positions/', { params })
}

/**
 * 获取持仓汇总
 */
export const getPositionSummary = (account_id?: number): Promise<PositionSummary> => {
  return apiClient.get('/positions/summary', { params: { account_id } })
}

/**
 * 获取指定账户的持仓
 */
export const getAccountPositions = (account_id: number): Promise<Position[]> => {
  return apiClient.get(`/positions/account/${account_id}`)
}

/**
 * 获取持仓详情
 */
export const getPositionDetail = (position_id: number): Promise<Position> => {
  return apiClient.get(`/positions/${position_id}`)
}

/**
 * 获取重仓股列表
 */
export const getTopHoldings = (params?: {
  limit?: number
  by?: 'value' | 'pnl' | 'pnl_pct'
}): Promise<Position[]> => {
  return apiClient.get('/positions/holdings/top', { params })
}
