<template>
  <div class="sort-controls">
    <div class="sort-buttons">
      <v-btn
        class="sort-btn"
        :class="{ active: sortType === 'date' }"
        @click="handleSortType('date')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-clock-outline</v-icon>
        <span>按时间</span>
        <v-icon size="14" v-if="sortType === 'date'">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>

      <v-btn
        class="sort-btn"
        :class="{ active: sortType === 'translation' }"
        @click="handleSortType('translation')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-translate</v-icon>
        <span>按翻译</span>
        <v-icon size="14" v-if="sortType === 'translation'">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>

      <v-btn
        class="sort-btn"
        :class="{ active: sortType === 'relevance' }"
        @click="handleSortType('relevance')"
        size="small"
        rounded="lg"
      >
        <v-icon size="16">mdi-star-outline</v-icon>
        <span>按相关性</span>
        <v-icon size="14" v-if="sortType === 'relevance'">
          {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
        </v-icon>
      </v-btn>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  sortType: {
    type: String,
    required: true
  },
  sortOrder: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:sortType', 'update:sortOrder', 'sort-change']);

const handleSortType = (type) => {
  let newSortOrder = props.sortOrder;
  
  if (props.sortType === type) {
    // If clicking the same sort type, toggle sort order
    newSortOrder = props.sortOrder === "asc" ? "desc" : "asc";
  } else {
    // If clicking different sort type, set new type and reset to ascending
    newSortOrder = "asc";
  }
  
  emit('update:sortType', type);
  emit('update:sortOrder', newSortOrder);
  emit('sort-change', { sortType: type, sortOrder: newSortOrder });
};
</script>

<style scoped>
/* Import shared sort styles */
@import '@/styles/SortControls.css';

/* Override for inline usage in section header */
.sort-controls {
  padding: 0;
  background-color: transparent;
  justify-content: flex-end;
}

.sort-buttons {
  background: transparent;
  border: none;
  padding: 0;
}
</style>
