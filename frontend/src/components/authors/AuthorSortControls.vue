<template>
  <div class="sort-controls">
    <div class="sort-buttons">
      <v-btn
        :class="['sort-btn', { active: sortBy === 'name' }]"
        @click="handleSortBy('name')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-sort-alphabetical-variant</v-icon>
        <span>名称</span>
        <v-icon v-if="sortBy === 'name'" size="14">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>

      <v-btn
        :class="['sort-btn', { active: sortBy === 'worksCount' }]"
        @click="handleSortBy('worksCount')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-chart-bar</v-icon>
        <span>视频数</span>
        <v-icon v-if="sortBy === 'worksCount'" size="14">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>

      <v-btn
        :class="['sort-btn', { active: sortBy === 'lastUpdate' }]"
        @click="handleSortBy('lastUpdate')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-clock-outline</v-icon>
        <span>最近更新</span>
        <v-icon v-if="sortBy === 'lastUpdate'" size="14">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>

      <ListFilterMenu
        mode="authors"
        :model-value="filters"
        :max-works="maxWorks"
        :max-duration="maxDuration"
        :active-count="activeFilterCount"
        @apply="$emit('filter-apply', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { useSortControl } from "@/composables/useSortControl.js";

import ListFilterMenu from "@/components/filters/ListFilterMenu.vue";

const props = defineProps({
  sortBy: {
    type: String,
    required: true,
  },
  sortOrder: {
    type: String,
    required: true,
  },
  filters: { type: Object, required: true },
  maxWorks: { type: Number, default: 1 },
  maxDuration: { type: Number, default: 1800 },
  activeFilterCount: { type: Number, default: 0 },
});

const emit = defineEmits([
  "update:sortBy",
  "update:sortOrder",
  "sort-change",
  "filter-apply",
]);

const handleSortBy = useSortControl(props, emit, {
  defaultOrder: (field) => (field === "name" ? "asc" : "desc"),
});
</script>

<style scoped>
/* Import shared sort styles */
@import "@/styles/SortControls.css";
</style>
