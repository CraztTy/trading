import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/strategies',
      name: 'strategies',
      component: () => import('../views/StrategiesView.vue')
    },
    {
      path: '/backtest',
      name: 'backtest',
      component: () => import('../views/BacktestView.vue')
    },
    {
      path: '/live',
      name: 'live',
      component: () => import('../views/LiveView.vue')
    },
    {
      path: '/intelligence',
      name: 'intelligence',
      component: () => import('../views/IntelligenceView.vue')
    },
    {
      path: '/macro',
      name: 'macro',
      component: () => import('../views/MacroView.vue')
    },
    {
      path: '/industry',
      name: 'industry',
      component: () => import('../views/IndustryView.vue')
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue')
    }
  ]
})

export default router
