<template>
  <div class="metric-card" :class="{ large }">
    <div class="metric-header">
      <span class="metric-label">{{ label }}</span>
      <span class="metric-trend" :class="{ up: positive, down: negative }">{{ trend }}</span>
    </div>
    <div class="metric-value" :class="{ positive, negative }">{{ value }}</div>
    <div class="metric-sub">{{ subtext }}</div>
    <div v-if="large" class="sparkline"></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string
  trend: string
  subtext: string
  large?: boolean
  positive?: boolean
  negative?: boolean
}>()
</script>

<style scoped>
.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 0.75rem;
  padding: 1.5rem;
  transition: all 0.25s ease;
}

.metric-card:hover {
  border-color: var(--border-secondary);
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
}

.metric-card.large {
  grid-column: span 2;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.metric-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.metric-trend {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

.metric-trend.up {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-success);
}

.metric-trend.down {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.metric-value.positive {
  color: var(--accent-success);
}

.metric-value.negative {
  color: var(--accent-danger);
}

.metric-sub {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.sparkline {
  height: 40px;
  margin-top: 1rem;
  background: linear-gradient(to top, rgba(245, 158, 11, 0.1), transparent);
  border-radius: 0.25rem;
  position: relative;
  overflow: hidden;
}

.sparkline::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent-primary);
}

@media (max-width: 768px) {
  .metric-card.large {
    grid-column: span 1;
  }
}
</style>
