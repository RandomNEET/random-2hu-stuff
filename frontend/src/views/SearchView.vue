<template>
  <div class="search-container">
    <div class="search-content">
      <h1 class="search-title">搜索结果</h1>

      <div class="search-info" v-if="searchQuery">
        <p class="search-query">
          搜索关键词：<span class="query-text">"{{ searchQuery }}"</span>
        </p>
        <p class="search-stats">
          <span v-if="searchType === 'authors'"
            >找到 {{ filteredAuthors.length }} 个作者</span
          >
          <span v-else>找到 {{ searchedVideos.length }} 个视频</span>
        </p>
      </div>

      <!-- Video search results section -->
      <div
        v-if="searchType === 'videos' && searchedVideos.length > 0"
        class="results-section"
      >
        <div class="section-header">
          <h2 class="section-title">相关视频</h2>

          <!-- Sort controls -->
          <SearchSortControls
            v-model:sort-type="sortType"
            v-model:sort-order="sortOrder"
            @sort-change="handleSortChange"
          />
        </div>

        <div class="videos-list">
          <VideoGroup
            v-for="group in groupedSearchedVideos"
            :key="`group-${group.id}`"
            :group="group"
            show-author
            @author-click="goToAuthor"
          />
        </div>
      </div>

      <!-- Author search results -->
      <div
        v-if="searchType === 'authors' && filteredAuthors.length > 0"
        class="results-section"
      >
        <h2 class="section-title">相关作者</h2>
        <AuthorSearchGrid :authors="filteredAuthors" />
      </div>

      <!-- Loading and no results states -->
      <SearchResultsState
        :is-loading="isSearching"
        :has-query="!!searchQuery"
        :has-results="hasResults"
      />
    </div>

    <!-- Back to top button -->
    <BackToTop />
  </div>
</template>

<script setup>
import SearchSortControls from "@/components/search/SearchSortControls.vue";
import VideoGroup from "@/components/videos/VideoGroup.vue";
import AuthorSearchGrid from "@/components/authors/AuthorSearchGrid.vue";
import SearchResultsState from "@/components/search/SearchResultsState.vue";
import BackToTop from "@/components/common/BackToTop.vue";
import { useSearchPage } from "@/composables/useSearchPage.js";

const {
  searchedVideos,
  searchQuery,
  isSearching,
  searchType,
  sortType,
  sortOrder,
  groupedSearchedVideos,
  hasResults,
  handleSortChange,
  filteredAuthors,
  goToAuthor,
} = useSearchPage();
</script>

<style scoped>
.search-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px;
  background: var(--color-base);
  min-height: calc(100vh - 70px);
}

.search-content {
  background: var(--color-surface-0);
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 8px 32px var(--color-black-30);
  border: 1px solid var(--color-surface-1);
}

.search-title {
  text-align: center;
  color: var(--color-yellow);
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 32px;
}

.search-info {
  text-align: center;
  margin-bottom: 32px;
  padding: 16px;
  background: var(--color-surface-1);
  border-radius: 12px;
}

.search-query {
  color: var(--color-text);
  font-size: 1.2rem;
  margin: 0 0 8px 0;
}

.query-text {
  color: var(--color-blue);
  font-weight: bold;
}

.search-stats {
  color: var(--color-text-muted);
  font-size: 1rem;
  margin: 0;
}

.results-section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.section-header :deep(.sort-controls) {
  margin: 0 0 0 auto;
  max-width: none;
}

.section-header .section-title {
  margin-bottom: 0;
}

.section-title {
  color: var(--color-mauve);
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 20px 0;
  border-bottom: 2px solid var(--color-surface-1);
  padding-bottom: 12px;
}

.videos-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

/* Responsive design */
@media (max-width: 834px) {
  .search-container {
    padding: 20px 16px;
  }

  .search-content {
    padding: 24px 20px;
  }

  .search-title {
    font-size: 2rem;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .section-title {
    font-size: 1.2rem;
  }
}
</style>
