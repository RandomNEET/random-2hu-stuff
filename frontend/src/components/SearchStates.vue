<template>
  <div>
    <!-- Loading state -->
    <div v-if="isLoading && hasQuery" class="loading-state">
      <v-progress-circular
        size="64"
        width="4"
        color="var(--color-blue)"
        indeterminate
      ></v-progress-circular>
      <h3>搜索中...</h3>
      <p>正在查找相关内容</p>
    </div>

    <!-- No results found -->
    <div v-if="showNoResults" class="no-results">
      <v-icon size="64" color="var(--color-overlay)">mdi-magnify-remove-outline</v-icon>
      <h3>未找到相关结果</h3>
      <p>尝试使用不同的关键词进行搜索</p>
      <v-btn color="primary" @click="$router.push('/')" class="back-home-btn">
        返回首页
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  isLoading: {
    type: Boolean,
    default: false,
  },
  hasQuery: {
    type: Boolean,
    default: false,
  },
  hasResults: {
    type: Boolean,
    default: false,
  },
});

const showNoResults = computed(() => {
  return !props.isLoading && props.hasQuery && !props.hasResults;
});
</script>

<style scoped>
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted); /* Catppuccin Mocha Subtext0 */
}

.loading-state h3 {
  color: var(--color-blue); /* Catppuccin Mocha Blue */
  margin: 16px 0 8px 0;
}

.loading-state p {
  margin-bottom: 24px;
  color: var(--color-text); /* Catppuccin Mocha Text */
}

.no-results {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted); /* Catppuccin Mocha Subtext0 */
}

.no-results h3 {
  color: var(--color-text); /* Catppuccin Mocha Text */
  margin: 16px 0 8px 0;
}

.no-results p {
  margin-bottom: 24px;
}

.back-home-btn {
  background: linear-gradient(90deg, var(--color-blue), var(--color-sapphire)) !important;
  color: var(--color-base) !important;
  font-weight: 600;
}
</style>
