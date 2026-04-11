/**
 * 认证相关API
 */
import apiClient from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  nickname?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: number
  username: string
  email: string
  nickname?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export interface PasswordChangeRequest {
  current_password: string
  new_password: string
}

/**
 * 用户登录
 */
export const login = (data: LoginRequest): Promise<TokenResponse> => {
  return apiClient.post('/auth/login', data)
}

/**
 * 用户注册
 */
export const register = (data: RegisterRequest): Promise<UserInfo> => {
  return apiClient.post('/auth/register', data)
}

/**
 * 刷新Token
 */
export const refreshToken = (refreshToken: string): Promise<TokenResponse> => {
  return apiClient.post('/auth/refresh', {}, {
    headers: { Authorization: `Bearer ${refreshToken}` }
  })
}

/**
 * 获取当前用户信息
 */
export const getCurrentUser = (): Promise<UserInfo> => {
  return apiClient.get('/auth/me')
}

/**
 * 修改密码
 */
export const changePassword = (data: PasswordChangeRequest): Promise<{ message: string }> => {
  return apiClient.post('/auth/password', data)
}

/**
 * 用户登出
 */
export const logout = (): Promise<{ message: string }> => {
  return apiClient.post('/auth/logout')
}
