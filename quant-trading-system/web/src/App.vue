<template>
  <div class="app-container">
    <Sidebar />
    <div class="main-content">
      <TopBar />
      <main class="page-container">
        <RouterView />
      </main>
    </div>
    <NotificationPanel />
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
  background: var(--bg-primary);
}

.main-content {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
}

.page-container {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .main-content {
    margin-left: 60px;
  }
}
</style>
