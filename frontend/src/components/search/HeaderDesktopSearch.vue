<template>
  <div class="search-container" ref="searchContainer">
    <div class="search-wrapper">
      <v-text-field
        v-model="searchForm.query"
        placeholder="搜索作者或视频..."
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        density="compact"
        hide-details
        class="search-field desktop-search"
        @focus="handleSearchFocus"
        @click="handleSearchClick"
        @input="handleSearchInput"
        @keyup.enter="performSearch"
      />

      <!-- Search Panel Dropdown -->
      <div v-if="showSearchPanel" class="search-panel" @click.stop>
        <!-- Search Type Selection -->
        <div class="search-type-section">
          <v-btn-toggle
            v-model="searchForm.type"
            color="primary"
            mandatory
            class="search-type-toggle"
          >
            <v-btn value="videos" class="search-type-btn">
              <v-icon size="small" class="mr-1">mdi-video</v-icon>
              视频
            </v-btn>
            <v-btn value="authors" class="search-type-btn">
              <v-icon size="small" class="mr-1">mdi-account</v-icon>
              作者
            </v-btn>
          </v-btn-toggle>
        </div>

        <!-- Video Filters -->
        <HeaderVideoFilters />

        <!-- Search Limit -->
        <div class="limit-section">
          <div class="limit-header">
            <span class="limit-label">搜索数量</span>
            <span class="limit-value">{{ searchForm.limit }}</span>
          </div>
          <v-slider
            v-model="searchForm.limit"
            :min="10"
            :max="searchForm.type === 'videos' ? 500 : 200"
            :step="10"
            color="var(--color-mauve)"
            track-color="var(--color-surface-2)"
            thumb-color="var(--color-mauve)"
            hide-details
            class="unified-slider"
          />
        </div>

        <!-- Action Buttons -->
        <div class="search-actions">
          <v-btn
            size="small"
            variant="outlined"
            color="surface-variant"
            @click="resetForm"
            class="action-btn reset-btn"
          >
            重置
          </v-btn>
          <v-btn
            size="small"
            color="primary"
            variant="flat"
            @click="performSearch"
            :disabled="!searchForm.query.trim() || !searchDurationValid"
            class="action-btn search-btn"
          >
            搜索
          </v-btn>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import HeaderVideoFilters from "./HeaderVideoFilters.vue";
import { useHeaderSearchContext } from "./headerSearchContext.js";

const {
  showSearchPanel,
  searchContainer,
  searchForm,
  searchDurationValid,
  resetForm,
  performSearch,
  handleSearchFocus,
  handleSearchClick,
  handleSearchInput,
} = useHeaderSearchContext();
</script>

<style scoped>
@import "./styles/search-sliders.css";
.search-container {
  max-width: 400px;
  width: 100%;
  position: relative;
  overflow: visible;
  z-index: 1000;
  margin: 0 auto;
}
.desktop-search {
  display: block; /* Show desktop search by default */
}
.search-field :deep(.v-field) {
  background-color: var(
    --color-surface-1
  ) !important; /* Catppuccin Mocha Surface1 */
  border-radius: 12px;
}
.search-field :deep(.v-field__input) {
  color: var(--color-text) !important; /* Catppuccin Mocha Text */
}
.search-field :deep(.v-field__outline) {
  border-color: var(
    --color-surface-2
  ) !important; /* Catppuccin Mocha Surface2 */
}
.search-field :deep(.v-field--focused .v-field__outline) {
  border-color: var(--color-blue) !important; /* Catppuccin Mocha Blue */
}
.search-field :deep(.v-field__prepend-inner .v-icon) {
  color: var(--color-text-muted) !important; /* Catppuccin Mocha Subtext0 */
}
.search-field :deep(::placeholder) {
  color: var(--color-overlay) !important; /* Catppuccin Mocha Overlay0 */
}
@media (max-width: 960px) {
  .search-container {
    display: none; /* Hide desktop search bar */
  }

  .desktop-search {
    display: none !important; /* Hide desktop search */
  }
}
.search-wrapper {
  position: relative;
  width: 100%;
  z-index: 1001;
}
.search-panel {
  position: fixed;
  background: var(--color-base);
  border: 1px solid var(--color-surface-1);
  border-radius: 12px;
  box-shadow: 0 8px 32px var(--color-black-40);
  z-index: 9999;
  padding: 16px;
  max-height: 80vh;
  overflow-y: auto;
  width: 560px;
  max-width: calc(100vw - 40px);
}
.limit-section {
  background: var(--color-surface-0);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--color-surface-1);
  margin-bottom: 16px;
}
.search-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--color-surface-1);
}
.action-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
}
@media (max-width: 600px) {
  .search-panel {
    left: 20px !important;
    width: calc(100vw - 40px) !important;
    border-radius: 8px;
    padding: 12px;
  }

  .limit-section {
    padding: 10px;
  }
}
.search-type-section {
  margin-bottom: 20px;
}
.search-type-toggle {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}
.search-type-btn {
  flex: 1;
  height: 40px;
  color: var(--color-text-muted) !important;
  background-color: var(--color-surface-1) !important;
  border: none !important;
  border-radius: 0 !important;
  font-weight: 500 !important;
  font-size: 0.9rem !important;
  transition: all 0.2s ease !important;
}
.search-type-btn:hover {
  background-color: var(--color-surface-2) !important;
  color: var(--color-text) !important;
}
.search-type-btn.v-btn--selected {
  background-color: var(--color-blue) !important;
  color: var(--color-base) !important;
  font-weight: 600 !important;
}
.search-type-btn:first-child {
  border-top-left-radius: 8px !important;
  border-bottom-left-radius: 8px !important;
}
.search-type-btn:last-child {
  border-top-right-radius: 8px !important;
  border-bottom-right-radius: 8px !important;
}
.limit-section {
  background: var(--color-surface-0);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--color-surface-1);
}
.limit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.limit-label {
  color: var(--color-text);
  font-size: 0.9rem;
  font-weight: 500;
}
.limit-value {
  color: var(--color-mauve);
  font-weight: 600;
  font-size: 1rem;
  background: var(--color-surface-1);
  padding: 4px 12px;
  border-radius: 16px;
  min-width: 50px;
  text-align: center;
}
.search-actions {
  background: transparent !important;
  padding: 16px 24px !important;
  border-top: 1px solid var(--color-surface-1);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
.action-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  min-width: 80px;
}
.reset-btn {
  background-color: transparent !important;
  border-color: var(--color-surface-2) !important;
  color: var(--color-text-muted) !important;
}
.reset-btn:hover {
  background-color: var(--color-surface-1) !important;
  border-color: var(--color-overlay) !important;
}
.search-btn {
  background-color: var(--color-blue) !important;
  color: var(--color-base) !important;
  box-shadow: 0 2px 8px var(--color-blue-30) !important;
}
.search-btn:hover {
  background-color: var(--color-sapphire) !important;
  box-shadow: 0 4px 12px var(--color-blue-40) !important;
}
@media (max-width: 600px) {
  .limit-section {
    padding: 16px;
  }
}
</style>
