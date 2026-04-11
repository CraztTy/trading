/**
 * 订单相关API
 */
import apiClient from './client'

export enum OrderDirection {
  BUY = 'buy',
  SELL = 'sell'
}

export enum OrderType {
  LIMIT = 'limit',
  MARKET = 'market'
}

export enum OrderStatus {
  CREATED = 'created',
  PENDING = 'pending',
  PARTIAL = 'partial',
  FILLED = 'filled',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected'
}

export interface Order {
  id?: number
  order_id: string
  account_id: number
  strategy_id?: number
  symbol: string
  direction: OrderDirection
  order_type: OrderType
  qty: number
  price?: number
  status: OrderStatus
  filled_qty: number
  remaining_qty: number
  filled_avg_price: number
  filled_amount: number
  created_at?: string
  submitted_at?: string
  filled_at?: string
  cancelled_at?: string
  error_msg?: string
}

export interface CreateOrderRequest {
  account_id: number
  symbol: string
  direction: OrderDirection
  qty: number
  price?: number
  order_type: OrderType
  strategy_id?: number
  symbol_name?: string
}

export interface OrderBookLevel {
  price: number
  volume: number
}

export interface OrderBook {
  symbol: string
  asks: OrderBookLevel[]
  bids: OrderBookLevel[]
  timestamp: string
}

/**
 * 创建订单
 */
export const createOrder = (data: CreateOrderRequest): Promise<Order> => {
  return apiClient.post('/orders/', data)
}

/**
 * 获取订单列表
 */
export const getOrders = (params?: {
  account_id?: number
  status?: OrderStatus
  limit?: number
  offset?: number
}): Promise<Order[]> => {
  return apiClient.get('/orders/', { params })
}

/**
 * 获取订单详情
 */
export const getOrderDetail = (orderId: string): Promise<Order> => {
  return apiClient.get(`/orders/${orderId}`)
}

/**
 * 撤销订单
 */
export const cancelOrder = (orderId: string): Promise<Order> => {
  return apiClient.post(`/orders/${orderId}/cancel`)
}

/**
 * 获取活跃订单
 */
export const getActiveOrders = (accountId: number): Promise<Order[]> => {
  return apiClient.get(`/orders/account/${accountId}/active`)
}

/**
 * 批量撤单
 */
export const cancelAllOrders = (accountId: number): Promise<{ account_id: number; cancelled_count: number }> => {
  return apiClient.post(`/orders/account/${accountId}/cancel-all`)
}

/**
 * 模拟订单成交（测试用）
 */
export const fillOrder = (orderId: string, fillQty: number, fillPrice: number): Promise<Order> => {
  return apiClient.post(`/orders/${orderId}/fill`, { fill_qty: fillQty, fill_price: fillPrice })
}

/**
 * 获取订单簿
 */
export const getOrderBook = (symbol: string): Promise<OrderBook> => {
  return apiClient.get(`/market/orderbook/${symbol}`)
}
