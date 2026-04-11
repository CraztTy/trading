/**
 * API客户端配置
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

// 创建axios实例
const apiClient = axios.create({
  baseURL: (import.meta as ImportMeta).env.VITE_API_BASE_URL || 'http://localhost:9000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  async (config) => {
    // 添加认证token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const originalRequest = error.config

    // 处理401错误 - Token过期
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // 尝试刷新token
        const authStore = useAuthStore()
        const refreshed = await authStore.tryRefreshToken()

        if (refreshed) {
          // 刷新成功，重试原请求
          const newToken = localStorage.getItem('access_token')
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return apiClient(originalRequest)
        } else {
          // 刷新失败，跳转登录页
          authStore.clearAuth()
          window.location.href = '/login'
          return Promise.reject(error)
        }
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    }

    // 显示错误消息
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)

    return Promise.reject(error)
  }
)

export default apiClient
