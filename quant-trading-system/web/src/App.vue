<template>
  <div class="app-container">
    <!-- 扫描线效果 -->
    <div class="scan-line"></div>

    <!-- 侧边栏 -->
    <Sidebar />

    <!-- 主内容区 -->
    <div class="main-content">
      <TopBar />
      <main class="page-container grid-bg">
        <RouterView v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>
    </div>

    <!-- 通知面板 -->
    <NotificationPanel />

    <!-- 背景装饰 -->
    <div class="ambient-glow ambient-glow-1"></div>
    <div class="ambient-glow ambient-glow-2"></div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './components/layout/Sidebar.vue'
import TopBar from './components/layout/TopBar.vue'
import NotificationPanel from './components/layout/NotificationPanel.vue'
import { useWebSocketStore } from './stores/websocket'
import { onMounted } from 'vue'

const wsStore = useWebSocketStore()

onMounted(() => {
  wsStore.connect()
})
</script>

<style>
.app-container {
  display: flex;
  min-height: 100vh;
  background: var(--bg-void);
  position: relative;
}

/* 环境辉光效果 */
.ambient-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(150px);
  pointer-events: none;
  z-index: 0;
}

.ambient-glow-1 {
  width: 600px;
  height: 600px;
  background: var(--neon-cyan);
  opacity: 0.03;
  top: -200px;
  right: -200px;
}

.ambient-glow-2 {
  width: 500px;
  height: 500px;
  background: var(--neon-magenta);
  opacity: 0.02;
  bottom: -150px;
  left: -150px;
}

.main-content {
  flex: 1;
  margin-left: 260px;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.page-container {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
  position: relative;
}

/* 页面切换动画 */
.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

@media (max-width: 1024px) {
  .main-content {
    margin-left: 70px;
  }

  .page-container {
    padding: 1rem;
  }
}
</style>
