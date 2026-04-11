/**
 * 持仓状态管理 (Pinia)
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  getPositions,
  getPositionSummary,
  getAccountPositions,
  type Position,
  type PositionSummary
} from '@/api/position'

// 重新导出类型
export type { Position, PositionSummary }

export const usePositionStore = defineStore('position', () => {
  // ============ State ============
  const positions = ref<Position[]>([])
  const summary = ref<PositionSummary | null>(null)
  const loading = ref(false)
  const currentAccountId = ref<number | null>(null)

  // ============ Getters ============
  const positionCount = computed(() => positions.value.length)

  const longPositions = computed(() =>
    positions.value.filter(p => p.total_qty > 0)
  )

  const profitablePositions = computed(() =>
    positions.value.filter(p => p.unrealized_pnl > 0)
  )

  const losingPositions = computed(() =>
    positions.value.filter(p => p.unrealized_pnl < 0)
  )

  const totalMarketValue = computed(() =>
    positions.value.reduce((sum, p) => sum + p.market_value, 0)
  )

  const totalUnrealizedPnl = computed(() =>
    positions.value.reduce((sum, p) => sum + p.unrealized_pnl, 0)
  )

  // ============ Actions ============

  /**
   * 加载持仓列表
   */
  const loadPositions = async (accountId?: number) => {
    loading.value = true
    try {
      const data = await getPositions({
        account_id: accountId,
        min_qty: 0
      })
      positions.value = data
      currentAccountId.value = accountId || null
    } catch (error: any) {
      ElMessage.error('加载持仓失败')
      console.error('加载持仓失败:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载持仓汇总
   */
  const loadSummary = async (accountId?: number) => {
    try {
      const data = await getPositionSummary(accountId)
      summary.value = data
    } catch (error: any) {
      console.error('加载持仓汇总失败:', error)
    }
  }

  /**
   * 加载指定账户的持仓
   */
  const loadAccountPositions = async (accountId: number) => {
    loading.value = true
    try {
      const data = await getAccountPositions(accountId)
      positions.value = data
      currentAccountId.value = accountId
    } catch (error: any) {
      ElMessage.error('加载账户持仓失败')
      console.error('加载账户持仓失败:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 刷新持仓数据
   */
  const refreshPositions = async () => {
    if (currentAccountId.value) {
      await loadAccountPositions(currentAccountId.value)
    } else {
      await loadPositions()
    }
    await loadSummary(currentAccountId.value || undefined)
  }

  /**
   * 清空持仓数据
   */
  const clearPositions = () => {
    positions.value = []
    summary.value = null
    currentAccountId.value = null
  }

  return {
    // State
    positions,
    summary,
    loading,
    currentAccountId,
    // Getters
    positionCount,
    longPositions,
    profitablePositions,
    losingPositions,
    totalMarketValue,
    totalUnrealizedPnl,
    // Actions
    loadPositions,
    loadSummary,
    loadAccountPositions,
    refreshPositions,
    clearPositions
  }
})
