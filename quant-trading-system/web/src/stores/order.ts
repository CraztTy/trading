/**
 * 订单状态管理 (Pinia)
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  createOrder as createOrderApi,
  getOrders as getOrdersApi,
  getOrderDetail as getOrderDetailApi,
  cancelOrder as cancelOrderApi,
  getActiveOrders as getActiveOrdersApi,
  cancelAllOrders as cancelAllOrdersApi,
  fillOrder as fillOrderApi,
  getOrderBook as getOrderBookApi,
  type Order,
  type CreateOrderRequest,
  type OrderBook,
  OrderDirection,
  OrderType,
  OrderStatus
} from '@/api/order'

export { OrderDirection, OrderType, OrderStatus }

export const useOrderStore = defineStore('order', () => {
  // ============ State ============
  const orders = ref<Order[]>([])
  const activeOrders = ref<Order[]>([])
  const currentOrder = ref<Order | null>(null)
  const orderBook = ref<OrderBook | null>(null)
  const loading = ref(false)
  const submitting = ref(false)

  // ============ Getters ============
  const pendingOrders = computed(() =>
    orders.value.filter(o => o.status === OrderStatus.PENDING || o.status === OrderStatus.CREATED)
  )

  const filledOrders = computed(() =>
    orders.value.filter(o => o.status === OrderStatus.FILLED)
  )

  const cancelledOrders = computed(() =>
    orders.value.filter(o => o.status === OrderStatus.CANCELLED || o.status === OrderStatus.REJECTED)
  )

  const totalOrderCount = computed(() => orders.value.length)

  // ============ Actions ============

  /**
   * 创建订单
   */
  const submitOrder = async (data: CreateOrderRequest): Promise<boolean> => {
    submitting.value = true
    try {
      const order = await createOrderApi(data)
      orders.value.unshift(order)
      ElMessage.success(`订单创建成功: ${order.order_id}`)
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || '订单创建失败'
      ElMessage.error(message)
      return false
    } finally {
      submitting.value = false
    }
  }

  /**
   * 加载订单列表
   */
  const loadOrders = async (params?: {
    account_id?: number
    status?: OrderStatus
    limit?: number
    offset?: number
  }) => {
    loading.value = true
    try {
      const data = await getOrdersApi(params)
      orders.value = data
    } catch (error: any) {
      console.error('加载订单失败:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载订单详情
   */
  const loadOrderDetail = async (orderId: string) => {
    try {
      const data = await getOrderDetailApi(orderId)
      currentOrder.value = data
      return data
    } catch (error: any) {
      ElMessage.error('加载订单详情失败')
      return null
    }
  }

  /**
   * 撤销订单
   */
  const cancelOrderById = async (orderId: string): Promise<boolean> => {
    try {
      await cancelOrderApi(orderId)
      // 更新本地订单状态
      const order = orders.value.find(o => o.order_id === orderId)
      if (order) {
        order.status = OrderStatus.CANCELLED
      }
      ElMessage.success('撤单成功')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || '撤单失败'
      ElMessage.error(message)
      return false
    }
  }

  /**
   * 加载活跃订单
   */
  const loadActiveOrders = async (accountId: number) => {
    try {
      const data = await getActiveOrdersApi(accountId)
      activeOrders.value = data
    } catch (error: any) {
      console.error('加载活跃订单失败:', error)
    }
  }

  /**
   * 批量撤单
   */
  const cancelAll = async (accountId: number): Promise<boolean> => {
    try {
      const result = await cancelAllOrdersApi(accountId)
      await loadOrders({ account_id: accountId })
      ElMessage.success(`成功撤销 ${result.cancelled_count} 个订单`)
      return true
    } catch (error: any) {
      ElMessage.error('批量撤单失败')
      return false
    }
  }

  /**
   * 模拟订单成交（测试用）
   */
  const simulateFill = async (orderId: string, fillQty: number, fillPrice: number): Promise<boolean> => {
    try {
      await fillOrderApi(orderId, fillQty, fillPrice)
      await loadOrderDetail(orderId)
      ElMessage.success('成交模拟成功')
      return true
    } catch (error: any) {
      ElMessage.error('成交模拟失败')
      return false
    }
  }

  /**
   * 加载订单簿
   */
  const loadOrderBook = async (symbol: string) => {
    try {
      const data = await getOrderBookApi(symbol)
      orderBook.value = data
    } catch (error: any) {
      console.error('加载订单簿失败:', error)
    }
  }

  /**
   * 清空订单数据
   */
  const clearOrders = () => {
    orders.value = []
    activeOrders.value = []
    currentOrder.value = null
    orderBook.value = null
  }

  return {
    // State
    orders,
    activeOrders,
    currentOrder,
    orderBook,
    loading,
    submitting,
    // Getters
    pendingOrders,
    filledOrders,
    cancelledOrders,
    totalOrderCount,
    // Actions
    submitOrder,
    loadOrders,
    loadOrderDetail,
    cancelOrderById,
    loadActiveOrders,
    cancelAll,
    simulateFill,
    loadOrderBook,
    clearOrders
  }
})
