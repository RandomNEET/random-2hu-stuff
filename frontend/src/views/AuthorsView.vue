<template>
  <div class="author-page">
    <!-- Sort controls -->
    <AuthorSortControls
      v-model:sort-by="sortBy"
      v-model:sort-order="sortOrder"
      :filters="authorFilters"
      :max-works="maxWorks"
      :max-duration="maxAverageDuration"
      :active-filter-count="activeFilterCount"
      @sort-change="handleSortChange"
      @filter-apply="handleFilterApply"
    />

    <!-- Author grid -->
    <AuthorGrid :authors="paginatedAuthors" />
    <div v-if="showFilterEmpty" class="filter-empty">
      没有符合当前筛选条件的作者
    </div>

    <!-- Pagination controls -->
    <ListPagination
      appearance="authors"
      v-model:current-page="currentPage"
      v-model:page-input="pageInput"
      :total-pages="totalPages"
      :window-width="windowWidth"
      @jump-to-page="jumpToPage"
      @go-to-page="goToPage"
    />

    <!-- Back to top button -->
    <BackToTop />

    <!-- SakanaWidget widget -->
    <SakanaWidget character="chisato" />
  </div>
</template>

<script setup>
import AuthorSortControls from "@/components/authors/AuthorSortControls.vue";
import AuthorGrid from "@/components/authors/AuthorGrid.vue";
import ListPagination from "@/components/common/ListPagination.vue";
import BackToTop from "@/components/common/BackToTop.vue";
import SakanaWidget from "@/components/widgets/SakanaWidget.vue";
import { useAuthorsPage } from "@/composables/useAuthorsPage.js";

const {
  showFilterEmpty,
  currentPage,
  pageInput,
  windowWidth,
  authorFilters,
  maxWorks,
  maxAverageDuration,
  activeFilterCount,
  sortBy,
  sortOrder,
  handleSortChange,
  handleFilterApply,
  totalPages,
  paginatedAuthors,
  goToPage,
  jumpToPage,
} = useAuthorsPage();
</script>

<style scoped>
.author-page {
  min-height: 100vh;
  background-color: var(--color-base);
}
.filter-empty {
  padding: 48px 24px;
  color: var(--color-text-muted);
  text-align: center;
}
</style>
