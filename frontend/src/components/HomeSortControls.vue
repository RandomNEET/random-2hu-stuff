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
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  sortBy: {
    type: String,
    required: true
  },
  sortOrder: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:sortBy', 'update:sortOrder', 'sort-change']);

const handleSortBy = (field) => {
  let newSortOrder = props.sortOrder;
  
  if (props.sortBy === field) {
    // If clicking the same field, toggle sort order
    newSortOrder = props.sortOrder === "asc" ? "desc" : "asc";
  } else {
    // If clicking different field, use default sort
    newSortOrder = field === "name" ? "asc" : "desc";
  }
  
  emit('update:sortBy', field);
  emit('update:sortOrder', newSortOrder);
  emit('sort-change', { sortBy: field, sortOrder: newSortOrder });
};
</script>

<style scoped>
/* Import shared sort styles */
@import '@/styles/SortControls.css';
</style>
