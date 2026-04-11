<template>
  <div class="recommendations">
    <div
      v-for="rec in recommendations"
      :key="rec.symbol"
      class="recommend-item"
    >
      <div class="rec-info">
        <span class="rec-symbol">{{ rec.symbol }}</span>
        <span class="rec-name">{{ rec.name }}</span>
        <div class="rec-tags">
          <el-tag
            v-for="tag in rec.tags"
            :key="tag"
            size="small"
            effect="dark"
            class="rec-tag"
          >
            {{ tag }}
          </el-tag>
        </div>
        <span class="rec-reason">{{ rec.reason }}</span>
      </div>
      <div class="rec-score">
        <div class="score-value">{{ rec.score }}分</div>
        <div class="score-label">多因子评分</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Recommendation {
  symbol: string
  name: string
  reason: string
  score: number
  tags: string[]
}

interface Props {
  recommendations: Recommendation[]
}

defineProps<Props>()
</script>

<style scoped lang="scss">
.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommend-item {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  transition: all 0.2s;
  cursor: pointer;

  &:hover {
    border-color: var(--accent-gold);
    transform: translateX(4px);
  }
}

.rec-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rec-symbol {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.rec-name {
  font-size: 12px;
  color: var(--text-muted);
}

.rec-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 4px 0;
}

.rec-tag {
  background: var(--bg-card) !important;
  border: none;
  color: var(--accent-gold);
}

.rec-reason {
  font-size: 11px;
  color: var(--accent-cyan);
}

.rec-score {
  text-align: right;
}

.score-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--accent-gold);
  font-family: var(--font-mono);
}

.score-label {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
