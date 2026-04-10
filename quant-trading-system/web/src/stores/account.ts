/**
 * 账户状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { accountApi, type Account } from '@/api'

export const useAccountStore = defineStore('account', () => {
  // State
  const accounts = ref<Account[]>([])
  const currentAccount = ref<Account | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const totalEquity = computed(() => {
    if (!currentAccount.value) return 0
    return currentAccount.value.available + currentAccount.value.frozen + currentAccount.value.market_value
  })

  const totalReturn = computed(() => {
    if (!currentAccount.value || currentAccount.value.initial_capital === 0) return 0
    return ((totalEquity.value - currentAccount.value.initial_capital) / currentAccount.value.initial_capital) * 100
  })

  const totalReturnPct = computed(() => totalReturn.value)

  // Actions
  async function fetchAccounts() {
    loading.value = true
    error.value = null
    try {
      const data = await accountApi.getAccounts()
      accounts.value = data
      // 默认选择第一个账户
      if (data.length > 0 && !currentAccount.value) {
        currentAccount.value = data[0]
      }
    } catch (err: any) {
      error.value = err.message
      console.error('获取账户失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchAccountDetail(accountId: number) {
    loading.value = true
    error.value = null
    try {
      const data = await accountApi.getAccount(accountId)
      currentAccount.value = data
    } catch (err: any) {
      error.value = err.message
      console.error('获取账户详情失败:', err)
    } finally {
      loading.value = false
    }
  }

  function setCurrentAccount(account: Account) {
    currentAccount.value = account
  }

  return {
    // State
    accounts,
    currentAccount,
    loading,
    error,
    // Getters
    totalEquity,
    totalReturn,
    totalReturnPct,
    // Actions
    fetchAccounts,
    fetchAccountDetail,
    setCurrentAccount
  }
})
