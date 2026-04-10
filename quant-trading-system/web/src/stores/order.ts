/**
 * 订单状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { orderApi, type Order, type CreateOrderRequest } from '@/api'

export const useOrderStore = defineStore('order', () => {
  // State
  const orders = ref<Order[]>([])
  const activeOrders = ref<Order[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const orderCount = computed(() => orders.value.length)

  const activeOrderCount = computed(() => activeOrders.value.length)

  const filledOrders = computed(() =>
    orders.value.filter(o => o.status === 'FILLED')
  )

  const pendingOrders = computed(() =>
    orders.value.filter(o => ['CREATED', 'PENDING', 'PARTIAL'].includes(o.status))
  )

  // Actions
  async function fetchOrders(accountId: number, status?: string) {
    loading.value = true
    error.value = null
    try {
      const data = await orderApi.getOrders(accountId, status)
      orders.value = data
    } catch (err: any) {
      error.value = err.message
      console.error('获取订单失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveOrders(accountId: number) {
    loading.value = true
    error.value = null
    try {
      const data = await orderApi.getActiveOrders(accountId)
      activeOrders.value = data
    } catch (err: any) {
      error.value = err.message
      console.error('获取活跃订单失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function createOrder(data: CreateOrderRequest) {
    loading.value = true
    error.value = null
    try {
      const newOrder = await orderApi.createOrder(data)
      orders.value.unshift(newOrder)
      return newOrder
    } catch (err: any) {
      error.value = err.message
      console.error('创建订单失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelOrder(orderId: string) {
    loading.value = true
    error.value = null
    try {
      const updatedOrder = await orderApi.cancelOrder(orderId)
      // 更新本地订单列表
      const index = orders.value.findIndex(o => o.order_id === orderId)
      if (index !== -1) {
        orders.value[index] = updatedOrder
      }
      // 从活跃订单中移除
      const activeIndex = activeOrders.value.findIndex(o => o.order_id === orderId)
      if (activeIndex !== -1) {
        activeOrders.value.splice(activeIndex, 1)
      }
      return updatedOrder
    } catch (err: any) {
      error.value = err.message
      console.error('撤单失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    orders,
    activeOrders,
    loading,
    error,
    // Getters
    orderCount,
    activeOrderCount,
    filledOrders,
    pendingOrders,
    // Actions
    fetchOrders,
    fetchActiveOrders,
    createOrder,
    cancelOrder
  }
})
