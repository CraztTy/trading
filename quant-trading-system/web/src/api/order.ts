/**
 * 订单 API
 */
import apiClient from './client'

export interface Order {
  id: number
  order_id: string
  account_id: number
  strategy_id?: number
  symbol: string
  symbol_name: string
  direction: 'BUY' | 'SELL'
  order_type: 'LIMIT' | 'MARKET' | 'STOP'
  qty: number
  price?: number
  status: 'CREATED' | 'PENDING' | 'PARTIAL' | 'FILLED' | 'CANCELLED' | 'REJECTED'
  filled_qty: number
  remaining_qty: number
  filled_avg_price: number
  filled_amount: number
  created_at: string
  submitted_at?: string
  filled_at?: string
  cancelled_at?: string
  error_msg?: string
}

export interface CreateOrderRequest {
  account_id: number
  symbol: string
  direction: 'BUY' | 'SELL'
  qty: number
  price?: number
  order_type?: 'LIMIT' | 'MARKET' | 'STOP'
  strategy_id?: number
  symbol_name?: string
}

export const orderApi = {
  /**
   * 获取账户订单列表
   */
  getOrders(accountId: number, status?: string): Promise<Order[]> {
    const params: any = { account_id: accountId }
    if (status) params.status = status
    return apiClient.get('/orders/', { params }) as Promise<Order[]>
  },

  /**
   * 获取活跃订单
   */
  getActiveOrders(accountId: number): Promise<Order[]> {
    return apiClient.get(`/orders/account/${accountId}/active`) as Promise<Order[]>
  },

  /**
   * 创建订单
   */
  createOrder(data: CreateOrderRequest): Promise<Order> {
    return apiClient.post('/orders/', data) as Promise<Order>
  },

  /**
   * 撤单
   */
  cancelOrder(orderId: string): Promise<Order> {
    return apiClient.post(`/orders/${orderId}/cancel`) as Promise<Order>
  }
}
