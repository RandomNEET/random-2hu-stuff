<template>
  <div class="sort-controls">
    <div class="sort-buttons">
      <v-btn
        class="sort-btn"
        :class="{ active: sortBy === 'date' }"
        @click="handleSortBy('date')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-clock-outline</v-icon>
        <span>按时间</span>
        <v-icon size="14" v-if="sortBy === 'date'">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>

      <v-btn
        class="sort-btn"
        :class="{ active: sortBy === 'translation' }"
        @click="handleSortBy('translation')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-translate</v-icon>
        <span>按翻译</span>
        <v-icon size="14" v-if="sortBy === 'translation'">
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

const handleSortBy = (type) => {
  let newSortOrder = props.sortOrder;
  
  if (props.sortBy === type) {
    // If clicking the same sort type, toggle sort order
    newSortOrder = props.sortOrder === "asc" ? "desc" : "asc";
  } else {
    // If clicking different sort type, set new type and reset to ascending
    newSortOrder = "asc";
  }
  
  emit('update:sortBy', type);
  emit('update:sortOrder', newSortOrder);
  emit('sort-change', { sortBy: type, sortOrder: newSortOrder });
};
</script>

<style scoped>
/* Import shared sort styles */
@import '@/styles/SortControls.css';
</style>
