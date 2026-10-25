<template>
  <div class="mobile-search-overlay" @click="showMobileSearch = false">
    <div class="mobile-search-popup" @click.stop>
      <!-- Close button -->
      <v-btn icon class="mobile-close-btn" @click="showMobileSearch = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>

      <!-- Mobile search title -->
      <h3 class="mobile-search-title">搜索</h3>

      <!-- Search input -->
      <v-text-field
        v-model="searchForm.query"
        placeholder="搜索作者或视频..."
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        density="compact"
        hide-details
        class="mobile-search-input"
        @keyup.enter="handleMobileSearch"
        autofocus
      />

      <!-- Search type selection -->
      <div class="mobile-search-types">
        <v-btn
          :variant="searchForm.type === 'videos' ? 'flat' : 'outlined'"
          :color="
            searchForm.type === 'videos' ? 'var(--color-mauve)' : 'default'
          "
          class="mobile-type-btn"
          @click="searchForm.type = 'videos'"
        >
          <v-icon left>mdi-video</v-icon>
          视频
        </v-btn>
        <v-btn
          :variant="searchForm.type === 'authors' ? 'flat' : 'outlined'"
          :color="
            searchForm.type === 'authors' ? 'var(--color-mauve)' : 'default'
          "
          class="mobile-type-btn"
          @click="searchForm.type = 'authors'"
        >
          <v-icon left>mdi-account</v-icon>
          作者
        </v-btn>
      </div>

      <!-- Filters (only show for video search) -->
      <HeaderVideoFilters mobile />

      <!-- Search Limit (show for both video and author search) -->
      <div class="mobile-filter-item">
        <label class="mobile-filter-label">搜索数量</label>
        <div class="mobile-limit-container">
          <v-slider
            v-model="searchForm.limit"
            :min="10"
            :max="searchForm.type === 'videos' ? 500 : 200"
            :step="10"
            variant="outlined"
            density="compact"
            color="var(--color-mauve)"
            track-color="var(--color-surface-2)"
            thumb-color="var(--color-mauve)"
            hide-details
            class="mobile-limit-slider unified-slider"
          />
          <span class="mobile-limit-value">{{ searchForm.limit }}</span>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="mobile-actions">
        <v-btn
          variant="outlined"
          class="mobile-reset-btn"
          @click="resetMobileSearch"
        >
          重置
        </v-btn>
        <v-btn
          variant="flat"
          color="var(--color-mauve)"
          class="mobile-search-action-btn"
          @click="handleMobileSearch"
          :disabled="!searchDurationValid"
        >
          搜索
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import HeaderVideoFilters from "./HeaderVideoFilters.vue";
import { useHeaderSearchContext } from "./headerSearchContext.js";

const {
  showMobileSearch,
  searchForm,
  searchDurationValid,
  handleMobileSearch,
  resetMobileSearch,
} = useHeaderSearchContext();
</script>

<style scoped>
@import "./styles/search-field-labels.css";
@import "./styles/search-sliders.css";
.mobile-search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: var(--color-black-70);
  z-index: 2000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 20px;
  overflow-y: auto;
}
.mobile-search-popup {
  background: var(--color-base);
  color: var(--color-text);
  border-radius: 14px;
  padding: 24px;
  width: 100%;
  max-width: 400px;
  max-height: 90vh;
  box-shadow: 0 12px 36px var(--color-deep-shadow-65);
  border: 1px solid var(--color-surface-2);
  position: relative;
  overflow-y: auto;
  margin-top: 60px;
}
.mobile-close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  color: var(--color-text) !important;
  z-index: 10;
}
.mobile-close-btn:hover {
  background-color: var(--color-red-10) !important;
  color: var(--color-red) !important;
}
.mobile-search-title {
  color: var(--color-yellow);
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 20px;
  text-align: center;
  font-family: "JetBrains Mono", monospace;
}
.mobile-search-input {
  margin-bottom: 20px;
}
.mobile-search-types {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.mobile-type-btn {
  flex: 1;
  font-family: "JetBrains Mono", monospace;
  font-weight: 500;
}
.mobile-search-popup :deep(.v-field) {
  color: var(--color-text) !important;
  background: var(--color-surface-0) !important;
  border-radius: 8px;
}
.mobile-search-popup :deep(.v-field__input),
.mobile-search-popup :deep(.v-label),
.mobile-search-popup :deep(input) {
  color: var(--color-text) !important;
}
.mobile-search-popup :deep(.v-field__outline) {
  color: var(--color-surface-2) !important;
}
.mobile-search-popup :deep(.v-field--focused .v-field__outline) {
  color: var(--color-mauve) !important;
}
.mobile-search-popup :deep(.v-field__append-inner),
.mobile-search-popup :deep(.v-field__clearable) {
  color: var(--color-text-muted) !important;
}
.mobile-limit-container {
  display: flex;
  align-items: center;
  gap: 16px;
}
.mobile-limit-slider {
  flex: 1;
}
.mobile-limit-value {
  color: var(--color-mauve);
  font-size: 0.9rem;
  font-weight: 600;
  font-family: "JetBrains Mono", monospace;
  min-width: 40px;
  text-align: center;
  background: var(--color-mauve-10);
  border-radius: 8px;
  padding: 4px 8px;
  border: 1px solid var(--color-mauve-20);
}
.mobile-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  align-items: center;
}
.mobile-reset-btn,
.mobile-search-action-btn {
  flex: 1;
  font-family: "JetBrains Mono", monospace;
  font-weight: 500;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px !important;
}
@media (max-width: 600px) {
  .mobile-search-popup {
    width: 95%;
    padding: 16px;
  }
}
</style>
