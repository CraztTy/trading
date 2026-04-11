<template>
  <div class="quant-app">
    <!-- 未登录时显示登录页 -->
    <template v-if="!authStore.isLoggedIn && authStore.initialized">
      <RouterView />
    </template>

    <!-- 已登录时显示主布局 -->
    <template v-else-if="authStore.isLoggedIn">
      <TopBar />
      <SideBar />
      <main class="main-content">
        <RouterView v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>
    </template>

    <!-- 初始化中显示加载状态 -->
    <template v-else>
      <div class="init-loading">
        <el-icon class="loading-icon" size="48"><Loading /></el-icon>
        <p>加载中...</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import TopBar from './components/layout/TopBar.vue'
import SideBar from './components/layout/SideBar.vue'
import { useAuthStore } from './stores/auth'
import { useMarketStore } from './stores/market'
import { wsService } from './services/websocket'
import { monitoringWsService } from './services/monitoringWebsocket'

const authStore = useAuthStore()
const marketStore = useMarketStore()

onMounted(async () => {
  // 初始化认证状态
  await authStore.initAuth()

  // 如果已登录，初始化WebSocket连接
  if (authStore.isLoggedIn) {
    // 初始化行情数据WebSocket
    await marketStore.initWebSocket()

    // 初始化监控WebSocket
    await monitoringWsService.connect()

    // 订阅上证指数等大盘指数
    marketStore.subscribeSymbols(['000001.SH', '399001.SZ', '399006.SZ'])
  }
})

onUnmounted(() => {
  // 断开WebSocket连接
  wsService.disconnect()
  monitoringWsService.disconnect()
})
</script>

<style lang="scss">
.quant-app {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.main-content {
  margin-left: 260px;
  margin-top: 64px;
  padding: var(--space-6);
  min-height: calc(100vh - 64px);
  position: relative;
  z-index: 1;

  // 响应式：侧边栏折叠时
  @media (max-width: 1024px) {
    margin-left: 72px;
    padding: var(--space-4);
  }

  @media (max-width: 768px) {
    margin-left: 0;
    padding: var(--space-4);
  }
}

// 初始化加载状态
.init-loading {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  color: var(--text-secondary);

  .loading-icon {
    color: var(--accent-gold);
    animation: spin 1s linear infinite;
  }

  p {
    font-size: 0.9375rem;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 页面过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

// 全局工具类（可被所有组件使用）
.text-up {
  color: var(--accent-green) !important;
}

.text-down {
  color: var(--accent-red) !important;
}

.text-neutral {
  color: var(--text-muted) !important;
}

.text-gold {
  color: var(--accent-gold) !important;
}

.text-cyan {
  color: var(--accent-cyan) !important;
}

.text-purple {
  color: var(--accent-purple) !important;
}

// 滚动条美化
* {
  scrollbar-width: thin;
  scrollbar-color: var(--bg-elevated) var(--bg-secondary);
}

// 选中文字样式
::selection {
  background: rgba(212, 175, 55, 0.3);
  color: var(--text-primary);
}
</style>
