<template>
  <div class="metric-card">
    <div class="metric-header">
      <span class="metric-label">{{ title }}</span>
      <div :class="['metric-icon', color]">
        <el-icon size="20">
          <component :is="icon" />
        </el-icon>
      </div>
    </div>
    <div class="metric-value" :style="{ color: valueColor }">
      {{ value }}
    </div>
    <div class="metric-change">
      <span :class="['change-percent', changeType]">
        {{ change }}
      </span>
      <span v-if="period" class="change-label">{{ period }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  title: string
  value: string
  change: string
  changeType: 'up' | 'down' | 'neutral'
  period: string
  icon: string
  color: string
}

const props = defineProps<Props>()

const valueColor = computed(() => {
  const colors: Record<string, string> = {
    gold: '#d4af37',
    cyan: '#00d4ff',
    green: '#00ff88',
    red: '#ff4757'
  }
  return colors[props.color] || '#ffffff'
})
</script>

<style scoped lang="scss">
.metric-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;

  &:hover {
    border-color: var(--border-glow);
    box-shadow: 0 0 30px rgba(212, 175, 55, 0.1);
  }

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent-gold), transparent);
    opacity: 0.5;
  }
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.metric-label {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;

  &.gold {
    background: rgba(212, 175, 55, 0.1);
    color: var(--accent-gold);
  }

  &.cyan {
    background: rgba(0, 212, 255, 0.1);
    color: var(--accent-cyan);
  }

  &.green {
    background: rgba(0, 255, 136, 0.1);
    color: var(--accent-green);
  }

  &.red {
    background: rgba(255, 71, 87, 0.1);
    color: var(--accent-red);
  }
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  letter-spacing: -1px;
  font-family: var(--font-mono);
}

.metric-change {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.change-percent {
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 600;

  &.up {
    color: var(--accent-green);
    background: rgba(0, 255, 136, 0.1);
  }

  &.down {
    color: var(--accent-red);
    background: rgba(255, 71, 87, 0.1);
  }

  &.neutral {
    color: var(--text-secondary);
    background: var(--bg-tertiary);
  }
}

.change-label {
  color: var(--text-muted);
}
</style>