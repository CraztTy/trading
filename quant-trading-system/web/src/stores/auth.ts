/**
 * 用户认证状态管理 (Pinia)
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  login as loginApi,
  register as registerApi,
  refreshToken as refreshTokenApi,
  getCurrentUser as getCurrentUserApi,
  logout as logoutApi,
  type LoginRequest,
  type RegisterRequest,
  type UserInfo,
  type TokenResponse
} from '@/api/auth'

// Token存储键名
const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const TOKEN_EXPIRES_KEY = 'token_expires_at'

export const useAuthStore = defineStore('auth', () => {
  // ============ State ============
  const user = ref<UserInfo | null>(null)
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const refreshTokenValue = ref<string>(localStorage.getItem(REFRESH_TOKEN_KEY) || '')
  const tokenExpiresAt = ref<number>(parseInt(localStorage.getItem(TOKEN_EXPIRES_KEY) || '0'))
  const loading = ref(false)
  const initialized = ref(false)

  // ============ Getters ============
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isTokenExpired = computed(() => {
    if (!tokenExpiresAt.value) return true
    // 提前5分钟认为过期
    return Date.now() >= (tokenExpiresAt.value - 5 * 60 * 1000)
  })
  const username = computed(() => user.value?.username || '')
  const nickname = computed(() => user.value?.nickname || user.value?.username || '')

  // ============ Actions ============

  /**
   * 初始化认证状态
   * 应用启动时调用，恢复登录状态
   */
  const initAuth = async (): Promise<boolean> => {
    if (initialized.value) return isLoggedIn.value

    const storedToken = localStorage.getItem(TOKEN_KEY)
    if (!storedToken) {
      initialized.value = true
      return false
    }

    try {
      // 获取当前用户信息验证token有效性
      const userInfo = await getCurrentUserApi()
      user.value = userInfo
      initialized.value = true
      return true
    } catch (error) {
      // Token无效，尝试刷新
      const refreshed = await tryRefreshToken()
      initialized.value = true
      return refreshed
    }
  }

  /**
   * 用户登录
   */
  const login = async (credentials: LoginRequest): Promise<boolean> => {
    loading.value = true
    try {
      const response: TokenResponse = await loginApi(credentials)
      setTokens(response)

      // 获取用户信息
      const userInfo = await getCurrentUserApi()
      user.value = userInfo

      ElMessage.success('登录成功')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || '登录失败'
      ElMessage.error(message)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户注册
   */
  const register = async (data: RegisterRequest): Promise<boolean> => {
    loading.value = true
    try {
      await registerApi(data)
      ElMessage.success('注册成功，请登录')
      return true
    } catch (error: any) {
      const message = error.response?.data?.detail || '注册失败'
      ElMessage.error(message)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户登出
   */
  const logout = async (): Promise<void> => {
    try {
      if (token.value) {
        await logoutApi()
      }
    } catch (error) {
      // 忽略登出接口错误
    } finally {
      clearAuth()
      ElMessage.success('已登出')
    }
  }

  /**
   * 尝试刷新Token
   */
  const tryRefreshToken = async (): Promise<boolean> => {
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!storedRefreshToken) {
      clearAuth()
      return false
    }

    try {
      const response = await refreshTokenApi(storedRefreshToken)
      setTokens(response)

      // 刷新成功后获取用户信息
      const userInfo = await getCurrentUserApi()
      user.value = userInfo
      return true
    } catch (error) {
      clearAuth()
      return false
    }
  }

  /**
   * 设置Token
   */
  const setTokens = (response: TokenResponse): void => {
    token.value = response.access_token
    refreshTokenValue.value = response.refresh_token

    // 计算过期时间
    const expiresAt = Date.now() + response.expires_in * 1000
    tokenExpiresAt.value = expiresAt

    // 持久化存储
    localStorage.setItem(TOKEN_KEY, response.access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, response.refresh_token)
    localStorage.setItem(TOKEN_EXPIRES_KEY, expiresAt.toString())
  }

  /**
   * 清除认证状态
   */
  const clearAuth = (): void => {
    user.value = null
    token.value = ''
    refreshTokenValue.value = ''
    tokenExpiresAt.value = 0

    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRES_KEY)
  }

  /**
   * 更新用户信息
   */
  const updateUserInfo = (info: Partial<UserInfo>): void => {
    if (user.value) {
      user.value = { ...user.value, ...info }
    }
  }

  return {
    // State
    user,
    token,
    loading,
    initialized,
    // Getters
    isLoggedIn,
    isTokenExpired,
    username,
    nickname,
    // Actions
    initAuth,
    login,
    register,
    logout,
    tryRefreshToken,
    clearAuth,
    updateUserInfo
  }
})
