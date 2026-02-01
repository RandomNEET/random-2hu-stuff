<template>
  <div class="pagination-container desktop-only" v-if="totalPages > 1 && !isMobile">
    <div class="pagination-wrapper">
      <!-- Previous page button -->
      <v-btn
        v-if="currentPage > 1"
        icon
        size="small"
        class="nav-button"
        @click="emit('update:currentPage', currentPage - 1)"
      >
        <v-icon>mdi-chevron-left</v-icon>
      </v-btn>

      <!-- Page number buttons -->
      <div class="page-numbers">
        <!-- Dynamic page display -->
        <template
          v-for="item in pageItems"
          :key="item.page || item.type"
        >
          <!-- Regular page number -->
          <v-btn
            v-if="item.type === 'page'"
            :class="['page-btn', { active: currentPage === item.page }]"
            @click="emit('update:currentPage', item.page)"
            size="small"
            rounded="xl"
          >
            {{ item.page }}
          </v-btn>

          <!-- Ellipsis -->
          <v-btn
            v-else-if="item.type === 'ellipsis'"
            class="ellipsis-btn"
            @click="emit('jump-to-page', item.targetPage)"
            size="small"
            rounded="xl"
          >
            ...
          </v-btn>
        </template>
      </div>

      <!-- Next page button -->
      <v-btn
        v-if="currentPage < totalPages"
        icon
        size="small"
        class="nav-button"
        @click="emit('update:currentPage', currentPage + 1)"
      >
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>

      <!-- Manual page input -->
      <div class="page-input-section">
        <span class="page-input-label">跳至</span>
        <v-text-field
          :model-value="pageInputValue"
          @update:model-value="emit('update:pageInput', $event)"
          type="number"
          :min="1"
          :max="totalPages"
          class="page-input"
          variant="outlined"
          density="compact"
          hide-details
          @keyup.enter="emit('go-to-page')"
        ></v-text-field>
        <span class="page-unit-label">页</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  currentPage: {
    type: Number,
    required: true
  },
  totalPages: {
    type: Number,
    required: true
  },
  windowWidth: {
    type: Number,
    required: true
  },
  pageInputValue: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:currentPage', 'update:pageInput', 'jump-to-page', 'go-to-page']);

const isMobile = computed(() => props.windowWidth <= 768);

// Get page items array (including page numbers and ellipsis)
const pageItems = computed(() => {
  const current = props.currentPage;
  const total = props.totalPages;
  const items = [];

  // Decide display strategy based on screen size
  const isMobileView = props.windowWidth <= 768;
  const maxDisplayPages = isMobileView ? 5 : 9;
  const ellipsisThreshold = isMobileView ? 3 : 5;

  // If total pages <= max display pages, show all page numbers
  if (total <= maxDisplayPages) {
    for (let i = 1; i <= total; i++) {
      items.push({ type: "page", page: i });
    }
    return items;
  }

  // Case when total pages > max display pages
  const showLeftEllipsis = current >= ellipsisThreshold;
  const showRightEllipsis = current <= total - (ellipsisThreshold - 1);

  if (isMobileView) {
    // Mobile logic: maximum 5 elements (including ellipsis)
    if (showLeftEllipsis && showRightEllipsis) {
      // Both sides have ellipsis: 1 ... current ... total (5 elements)
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: Math.max(1, current - 1) });
      items.push({ type: "page", page: current });
      items.push({
        type: "ellipsis",
        targetPage: Math.min(total, current + 1),
      });
      items.push({ type: "page", page: total });
    } else if (showLeftEllipsis) {
      // Only left ellipsis: 1 ... current-1 current total (5 elements)
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: Math.max(1, current - 1) });
      if (current > total - 1) {
        items.push({ type: "page", page: total - 1 });
      } else {
        items.push({ type: "page", page: current - 1 });
      }
      items.push({ type: "page", page: current });
      items.push({ type: "page", page: total });
    } else if (showRightEllipsis) {
      // Only right ellipsis: 1 current current+1 ... total (5 elements)
      items.push({ type: "page", page: 1 });
      if (current === 1) {
        items.push({ type: "page", page: 2 });
        items.push({ type: "page", page: 3 });
      } else {
        items.push({ type: "page", page: current });
        items.push({ type: "page", page: current + 1 });
      }
      items.push({
        type: "ellipsis",
        targetPage: Math.min(total, current + 2),
      });
      items.push({ type: "page", page: total });
    } else {
      // No ellipsis: show all page numbers
      for (let i = 1; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    }
  } else {
    // Desktop logic: maintain original 9-page logic
    if (showLeftEllipsis && showRightEllipsis) {
      // Both sides have ellipsis: 1 ... current-2 current-1 current current+1 current+2 ... total
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: current - 3 });
      for (let i = current - 2; i <= current + 2; i++) {
        items.push({ type: "page", page: i });
      }
      items.push({ type: "ellipsis", targetPage: current + 3 });
      items.push({ type: "page", page: total });
    } else if (showLeftEllipsis) {
      // Only left ellipsis: 1 ... current-2 current-1 current current+1 current+2 ... total
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: current - 3 });
      for (let i = current - 2; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    } else if (showRightEllipsis) {
      // Only right ellipsis: 1 2 3 4 5 current current+1 current+2 ... total
      for (let i = 1; i <= current + 2; i++) {
        items.push({ type: "page", page: i });
      }
      items.push({ type: "ellipsis", targetPage: current + 3 });
      items.push({ type: "page", page: total });
    } else {
      // No ellipsis: show all page numbers (this case is handled when total <= 9)
      for (let i = 1; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    }
  }

  return items;
});
</script>

<style scoped>
@import '@/styles/PaginationControls.css';

/* Desktop-only display control */
.desktop-only {
  display: none;
}
@media (min-width: 769px) {
  .desktop-only {
    display: flex;
  }
}
.pagination-container {
  display: flex;
  justify-content: center;
  padding: 24px;
  background-color: #1e1e2e;
}
.pagination-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 30, 46, 0.8);
  padding: 12px 16px;
  border-radius: 16px;
  border: 1px solid rgba(203, 166, 247, 0.3);
}
.page-numbers {
  display: flex;
  align-items: center;
  gap: 4px;
}
.nav-button {
  background-color: rgba(49, 50, 68, 0.8) !important;
  color: #cdd6f4 !important;
  border: 1px solid rgba(203, 166, 247, 0.3) !important;
}
.nav-button:hover {
  background-color: rgba(203, 166, 247, 0.2) !important;
  color: #cba6f7 !important;
}
.page-btn {
  background-color: rgba(49, 50, 68, 0.8) !important;
  color: #cdd6f4 !important;
  border: 1px solid rgba(203, 166, 247, 0.3) !important;
  min-width: 36px !important;
  height: 36px !important;
}
.page-btn:hover {
  background-color: rgba(203, 166, 247, 0.2) !important;
  color: #cba6f7 !important;
}
.page-btn.active {
  background-color: #cba6f7 !important;
  color: #1e1e2e !important;
  border-color: #cba6f7 !important;
}
.ellipsis-btn {
  background-color: rgba(49, 50, 68, 0.8) !important;
  color: #89b4fa !important;
  border: 1px solid rgba(137, 180, 250, 0.3) !important;
  min-width: 36px !important;
  height: 36px !important;
}
.ellipsis-btn:hover {
  background-color: rgba(137, 180, 250, 0.2) !important;
  color: #74c7ec !important;
}
.page-input-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
  padding-left: 16px;
  border-left: 1px solid rgba(203, 166, 247, 0.3);
}
.page-input-label {
  color: #cdd6f4;
  font-size: 0.9rem;
  font-weight: 500;
}
.page-unit-label {
  color: #cdd6f4;
  font-size: 0.9rem;
  font-weight: 500;
}
.page-input {
  width: 60px !important;
}
.page-input :deep(.v-field) {
  background-color: rgba(49, 50, 68, 0.8) !important;
  border-radius: 8px !important;
}
.page-input :deep(.v-field__input) {
  color: #cdd6f4 !important;
  text-align: center;
  padding: 4px 8px !important;
  min-height: 32px !important;
}
.page-input :deep(.v-field__outline) {
  border-color: rgba(203, 166, 247, 0.4) !important;
}
.page-input :deep(.v-field--focused .v-field__outline) {
  border-color: #cba6f7 !important;
}
@media (max-width: 768px) {
  .pagination-wrapper {
    flex-wrap: wrap;
    padding: 8px 12px;
    gap: 6px;
    max-width: 100%;
    overflow-x: auto;
  }
  .page-numbers {
    gap: 2px;
  }
  .nav-button {
    min-width: 32px !important;
    height: 32px !important;
  }
  .page-btn {
    min-width: 32px !important;
    height: 32px !important;
    font-size: 0.8rem !important;
  }
  .ellipsis-btn {
    min-width: 32px !important;
    height: 32px !important;
    font-size: 0.8rem !important;
  }
  .page-input-section {
    margin-left: 8px;
    padding-left: 8px;
    gap: 4px;
  }
  .page-input-label {
    font-size: 0.8rem;
  }
  .page-unit-label {
    font-size: 0.8rem;
  }
  .page-input {
    width: 50px !important;
  }
  .page-input :deep(.v-field__input) {
    padding: 2px 4px !important;
    min-height: 28px !important;
    font-size: 0.8rem !important;
  }
}
@media (max-width: 480px) {
  .pagination-container {
    padding: 16px 8px;
  }
  .pagination-wrapper {
    flex-direction: column;
    align-items: center;
    padding: 6px 8px;
    gap: 4px;
    border-radius: 12px;
  }
  .page-numbers {
    gap: 0px;
    justify-content: center;
    width: 100%;
  }
  .page-input-section {
    justify-content: center;
    width: 100px;
    margin-top: 4px;
    margin-left: 0;
    padding-left: 0;
    gap: 3px;
    border-left: none;
  }
  .nav-button {
    max-width: 28px !important;
    height: 28px !important;
  }
  .page-btn {
    max-width: 28px !important;
    height: 28px !important;
    font-size: 0.75rem !important;
  }
  .ellipsis-btn {
    max-width: 28px !important;
    height: 28px !important;
    font-size: 0.75rem !important;
  }
  .page-input-label {
    font-size: 0.75rem;
  }
  .page-unit-label {
    font-size: 0.75rem;
  }
  .page-input {
    width: 45px !important;
  }
  .page-input :deep(.v-field__input) {
    padding: 2px 3px !important;
    min-height: 26px !important;
    font-size: 0.75rem !important;
  }
}
</style>
