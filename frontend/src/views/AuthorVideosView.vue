<template>
  <div class="video-list-container">
    <!-- Author information header -->
    <AuthorHeader :author="author" :video-count="originalVideos.length" />

    <!-- Sort controls -->
    <VideoSortControls
      v-model:sort-by="sortBy"
      v-model:sort-order="sortOrder"
      :filters="videoFilters"
      :max-duration="maxVideoDuration"
      :active-filter-count="activeFilterCount"
      @sort-change="handleSortChange"
      @filter-apply="handleFilterApply"
    />

    <!-- Video list -->
    <div class="videos-grid">
      <VideoGroup
        v-for="group in paginatedVideoGroups"
        :key="`group-${group.id}`"
        :group="group"
      />
      <div v-if="showFilterEmpty" class="filter-empty">
        没有符合当前筛选条件的视频
      </div>
    </div>

    <!-- Pagination -->
    <ListPagination
      v-if="totalPages > 1"
      v-model:current-page="currentPage"
      v-model:page-input="pageInput"
      :total-pages="totalPages"
      :window-width="9999"
      @jump-to-page="jumpToPage"
      @go-to-page="goToPage"
    />

    <!-- Back to top button -->
    <BackToTop />
  </div>
</template>

<script setup>
import AuthorHeader from "@/components/authors/AuthorHeader.vue";
import VideoSortControls from "@/components/videos/VideoSortControls.vue";
import VideoGroup from "@/components/videos/VideoGroup.vue";
import ListPagination from "@/components/common/ListPagination.vue";
import BackToTop from "@/components/common/BackToTop.vue";
import { useAuthorVideosPage } from "@/composables/useAuthorVideosPage.js";

const {
  videos,
  originalVideos,
  author,
  showFilterEmpty,
  currentPage,
  pageInput,
  videoFilters,
  maxVideoDuration,
  activeFilterCount,
  sortBy,
  sortOrder,
  handleSortChange,
  handleFilterApply,
  totalPages,
  paginatedVideoGroups,
  goToPage,
  jumpToPage,
} = useAuthorVideosPage();
</script>

<style scoped>
.video-list-container {
  max-width: 1200px;
  margin: 20px auto;
  background: var(--color-base); /* Catppuccin Mocha Base */
  border-radius: 20px;
  box-shadow: 0 8px 32px var(--color-black-30);
  padding: 0;
  overflow: hidden;
}

/* Video list */
.videos-grid {
  padding: 24px;
}
.filter-empty {
  padding: 48px 24px;
  color: var(--color-text-muted);
  text-align: center;
}

/* Responsive design */
@media (max-width: 834px) {
  .video-list-container {
    max-width: 95%;
    margin: 16px auto;
  }

  .videos-grid {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .videos-grid {
    padding: 12px;
  }
}
</style>
