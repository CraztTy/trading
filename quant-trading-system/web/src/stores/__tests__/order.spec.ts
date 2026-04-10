/**
 * Order Store 单元测试
 *
 * 测试Pinia状态管理的订单状态
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useOrderStore } from '../order'
import type { Order } from '../../api/order'

// Mock API模块
vi.mock('../../api/order', () => ({
  fetchOrders: vi.fn(),
  createOrder: vi.fn(),
  cancelOrder: vi.fn(),
  fetchOrderById: vi.fn()
}))

describe('Order Store', () => {
  beforeEach(() => {
    // 创建新的Pinia实例
    setActivePinia(createPinia())
  })

  describe('State Management', () => {
    it('should have correct initial state', () => {
      const store = useOrderStore()

      expect(store.orders).toEqual([])
      expect(store.activeOrders).toEqual([])
      expect(store.currentOrder).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should update orders state', () => {
      const store = useOrderStore()
      const mockOrders: Order[] = [
        {
          id: 1,
          order_id: 'ORD001',
          symbol: '000001.SZ',
          direction: 'BUY',
          qty: 1000,
          price: 10.5,
          status: 'PENDING',
          filled_qty: 0,
          remaining_qty: 1000
        }
      ]

      store.orders = mockOrders

      expect(store.orders).toHaveLength(1)
      expect(store.orders[0].order_id).toBe('ORD001')
    })
  })

  describe('Getters', () => {
    it('should return orders filtered by status', () => {
      const store = useOrderStore()
      store.orders = [
        { id: 1, order_id: 'ORD001', status: 'PENDING' },
        { id: 2, order_id: 'ORD002', status: 'FILLED' },
        { id: 3, order_id: 'ORD003', status: 'CANCELLED' }
      ] as Order[]

      const pendingOrders = store.getOrdersByStatus('PENDING')

      expect(pendingOrders).toHaveLength(1)
      expect(pendingOrders[0].order_id).toBe('ORD001')
    })

    it('should calculate total order value correctly', () => {
      const store = useOrderStore()
      store.orders = [
        { id: 1, order_id: 'ORD001', qty: 1000, price: 10, filled_qty: 500, filled_avg_price: 10 },
        { id: 2, order_id: 'ORD002', qty: 2000, price: 20, filled_qty: 2000, filled_avg_price: 20 }
      ] as Order[]

      const totalValue = store.totalOrderValue

      // (500 * 10) + (2000 * 20) = 5000 + 40000 = 45000
      expect(totalValue).toBe(45000)
    })
  })

  describe('Actions', () => {
    it('should handle loading state', async () => {
      const store = useOrderStore()
      const { fetchOrders } = await import('../../api/order')

      vi.mocked(fetchOrders).mockResolvedValueOnce({
        data: [],
        total: 0
      })

      // 开始加载
      const promise = store.loadOrders(1)
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })

    it('should handle error state', async () => {
      const store = useOrderStore()
      const { fetchOrders } = await import('../../api/order')

      vi.mocked(fetchOrders).mockRejectedValueOnce(new Error('Network error'))

      await store.loadOrders(1)

      expect(store.error).toBe('Network error')
      expect(store.loading).toBe(false)
    })

    it('should add new order optimistically', async () => {
      const store = useOrderStore()
      const { createOrder } = await import('../../api/order')

      const newOrder: Partial<Order> = {
        symbol: '000001.SZ',
        direction: 'BUY',
        qty: 1000,
        price: 10.5
      }

      vi.mocked(createOrder).mockResolvedValueOnce({
        id: 1,
        order_id: 'ORD001',
        ...newOrder,
        status: 'CREATED'
      } as Order)

      await store.createNewOrder(newOrder)

      expect(store.orders).toHaveLength(1)
      expect(store.orders[0].symbol).toBe('000001.SZ')
    })

    it('should update order status via WebSocket', () => {
      const store = useOrderStore()
      store.orders = [
        { id: 1, order_id: 'ORD001', status: 'PENDING', filled_qty: 0 }
      ] as Order[]

      // 模拟WebSocket推送的状态更新
      store.handleOrderUpdate({
        order_id: 'ORD001',
        status: 'PARTIAL',
        filled_qty: 500
      })

      const updatedOrder = store.orders.find(o => o.order_id === 'ORD001')
      expect(updatedOrder?.status).toBe('PARTIAL')
      expect(updatedOrder?.filled_qty).toBe(500)
    })
  })

  describe('WebSocket Integration', () => {
    it('should handle order fill notification', () => {
      const store = useOrderStore()
      const addNotificationSpy = vi.fn()

      store.orders = [
        { id: 1, order_id: 'ORD001', status: 'PENDING', symbol: '000001.SZ' }
      ] as Order[]

      store.handleFillNotification({
        order_id: 'ORD001',
        fill_qty: 1000,
        fill_price: 10.5
      })

      const order = store.orders.find(o => o.order_id === 'ORD001')
      expect(order?.status).toBe('FILLED')
    })

    it('should handle batch order updates', () => {
      const store = useOrderStore()

      store.orders = [
        { id: 1, order_id: 'ORD001', status: 'PENDING' },
        { id: 2, order_id: 'ORD002', status: 'PENDING' }
      ] as Order[]

      store.handleBatchUpdate([
        { order_id: 'ORD001', status: 'FILLED' },
        { order_id: 'ORD002', status: 'CANCELLED' }
      ])

      expect(store.orders[0].status).toBe('FILLED')
      expect(store.orders[1].status).toBe('CANCELLED')
    })
  })
})
