import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '仪表盘', requiresAuth: true }
  },
  {
    path: '/market',
    name: 'Market',
    component: () => import('@/views/MarketView.vue'),
    meta: { title: '行情', requiresAuth: true }
  },
  {
    path: '/trade',
    name: 'Trade',
    component: () => import('@/views/TradeView.vue'),
    meta: { title: '交易', requiresAuth: true }
  },
  {
    path: '/positions',
    name: 'Positions',
    component: () => import('@/views/PositionsView.vue'),
    meta: { title: '持仓', requiresAuth: true }
  },
  {
    path: '/strategy',
    name: 'Strategy',
    component: () => import('@/views/StrategyView.vue'),
    meta: { title: '策略', requiresAuth: true }
  },
  {
    path: '/screener',
    name: 'Screener',
    component: () => import('@/views/ScreenerView.vue'),
    meta: { title: '选股', requiresAuth: true }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/ReportsView.vue'),
    meta: { title: '报告', requiresAuth: true }
  },
  {
    path: '/risk',
    name: 'Risk',
    component: () => import('@/views/RiskView.vue'),
    meta: { title: '风控', requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 认证守卫
router.beforeEach(async (to, _from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || ''} - QuantPro`

  const authStore = useAuthStore()

  // 初始化认证状态（如果还没初始化）
  if (!authStore.initialized) {
    await authStore.initAuth()
  }

  // 公开页面直接通过
  if (to.meta.public) {
    // 已登录用户访问登录页，重定向到首页
    if (authStore.isLoggedIn && to.path === '/login') {
      next('/')
      return
    }
    next()
    return
  }

  // 需要认证的路由
  if (to.meta.requiresAuth) {
    if (!authStore.isLoggedIn) {
      // 未登录，重定向到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }

  next()
})

export default router
