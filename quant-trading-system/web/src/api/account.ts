/**
 * 账户 API
 */
import apiClient from './client'

export interface Account {
  id: number
  account_no: string
  name: string
  account_type: string
  total_balance: number
  available: number
  frozen: number
  market_value: number
  realized_pnl: number
  unrealized_pnl: number
  initial_capital: number
  max_drawdown: number
  status: string
  created_at: string
  updated_at: string
}

export const accountApi = {
  /**
   * 获取账户列表
   */
  getAccounts(): Promise<Account[]> {
    return apiClient.get('/accounts/') as Promise<Account[]>
  },

  /**
   * 获取账户详情
   */
  getAccount(accountId: number): Promise<Account> {
    return apiClient.get(`/accounts/${accountId}`) as Promise<Account>
  }
}
