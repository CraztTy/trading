/**
 * 策略 API
 */
import apiClient from './client'

export interface Strategy {
  id: string
  name: string
  description: string
  status: 'active' | 'inactive' | 'paused'
  type: string
  params: Record<string, any>
  created_at: string
  activated_at?: string
  performance?: {
    return: number
    sharpe: number
    max_drawdown: number
  }
}

export const strategyApi = {
  /**
   * 获取策略列表
   */
  getStrategies(activeOnly: boolean = true): Promise<{ strategies: Strategy[]; total: number }> {
    return apiClient.get('/strategies/', { params: { active_only: activeOnly } }) as Promise<{ strategies: Strategy[]; total: number }>
  },

  /**
   * 激活策略
   */
  activateStrategy(strategyId: string): Promise<Strategy> {
    return apiClient.post(`/strategies/${strategyId}/activate`) as Promise<Strategy>
  },

  /**
   * 停用策略
   */
  deactivateStrategy(strategyId: string): Promise<Strategy> {
    return apiClient.post(`/strategies/${strategyId}/deactivate`) as Promise<Strategy>
  }
}
