/**
 * 策略状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { strategyApi, type Strategy } from '@/api'

export const useStrategyStore = defineStore('strategy', () => {
  // State
  const strategies = ref<Strategy[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const activeStrategies = computed(() =>
    strategies.value.filter(s => s.status === 'active')
  )

  const activeCount = computed(() => activeStrategies.value.length)

  // Actions
  async function fetchStrategies(activeOnly: boolean = true) {
    loading.value = true
    error.value = null
    try {
      const data = await strategyApi.getStrategies(activeOnly)
      strategies.value = data.strategies
    } catch (err: any) {
      error.value = err.message
      console.error('获取策略失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function activateStrategy(strategyId: string) {
    loading.value = true
    error.value = null
    try {
      const updated = await strategyApi.activateStrategy(strategyId)
      const index = strategies.value.findIndex(s => s.id === strategyId)
      if (index !== -1) {
        strategies.value[index] = updated
      }
    } catch (err: any) {
      error.value = err.message
      console.error('激活策略失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function deactivateStrategy(strategyId: string) {
    loading.value = true
    error.value = null
    try {
      const updated = await strategyApi.deactivateStrategy(strategyId)
      const index = strategies.value.findIndex(s => s.id === strategyId)
      if (index !== -1) {
        strategies.value[index] = updated
      }
    } catch (err: any) {
      error.value = err.message
      console.error('停用策略失败:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    strategies,
    loading,
    error,
    // Getters
    activeStrategies,
    activeCount,
    // Actions
    fetchStrategies,
    activateStrategy,
    deactivateStrategy
  }
})
