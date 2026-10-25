<template>
  <div
    v-if="searchForm.type === 'videos'"
    :class="mobile ? 'mobile-filters' : 'filters-section'"
  >
    <h4 v-if="mobile" class="mobile-filter-title">筛选条件</h4>

    <div :class="rowClass">
      <label :class="labelClass">作者</label>
      <v-combobox
        v-model="searchForm.filters.authorInput"
        :items="authorOptions"
        item-title="name"
        item-value="name"
        placeholder="输入或选择作者"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        auto-select-first
        :menu-props="{ closeOnContentClick: true, maxHeight: 200 }"
        :class="inputClass"
        @update:model-value="selectAuthor"
        @blur="blurAuthor"
      />
    </div>

    <div :class="rowClass">
      <label :class="labelClass">翻译状态</label>
      <v-select
        v-model="searchForm.filters.translationStatus"
        :items="translationOptions"
        item-title="title"
        item-value="value"
        :placeholder="mobile ? undefined : '选择翻译状态'"
        variant="outlined"
        density="compact"
        hide-details
        :class="inputClass"
      />
    </div>

    <div :class="rowClass">
      <label :class="labelClass">时间范围</label>
      <div :class="mobile ? 'mobile-date-fields' : 'date-range-container'">
        <DateFilterField
          v-model="searchForm.filters.dateFrom"
          label="开始日期"
          :class="mobile ? 'mobile-date-input' : 'date-input'"
        />
        <span v-if="!mobile" class="date-separator">至</span>
        <DateFilterField
          v-model="searchForm.filters.dateTo"
          label="结束日期"
          :class="mobile ? 'mobile-date-input' : 'date-input'"
        />
      </div>
    </div>

    <div :class="mobile ? rowClass : 'filter-row duration-filter-row'">
      <RangeFilterFields
        label="视频时长"
        :min-value="searchForm.filters.minDuration"
        :max-value="searchForm.filters.maxDuration"
        :slider-max="searchMaxDuration"
        :step="60"
        :scale="60"
        nonlinear-duration
        unit="分钟"
        flat
        @update:min-value="searchForm.filters.minDuration = $event"
        @update:max-value="searchForm.filters.maxDuration = $event"
      />
    </div>
    <v-switch
      v-model="searchForm.filters.includeUnknownDuration"
      label="包含未知时长"
      :disabled="!searchDurationActive"
      :color="mobile ? 'var(--color-mauve)' : 'primary'"
      density="compact"
      hide-details
    />
  </div>
</template>

<script setup>
import { computed } from "vue";
import DateFilterField from "@/components/filters/DateFilterField.vue";
import RangeFilterFields from "@/components/filters/RangeFilterFields.vue";
import { useHeaderSearchContext } from "./headerSearchContext.js";

const props = defineProps({ mobile: { type: Boolean, default: false } });
const {
  searchForm,
  searchMaxDuration,
  searchDurationActive,
  authorOptions,
  translationOptions,
  handleAuthorSelection,
  handleAuthorBlur,
  handleMobileAuthorSelection,
  handleMobileAuthorBlur,
} = useHeaderSearchContext();

const rowClass = computed(() =>
  props.mobile ? "mobile-filter-item" : "filter-row",
);
const labelClass = computed(() =>
  props.mobile ? "mobile-filter-label" : "filter-label",
);
const inputClass = computed(() =>
  props.mobile ? "mobile-filter-input" : "filter-input",
);
const selectAuthor = (value) =>
  props.mobile
    ? handleMobileAuthorSelection(value)
    : handleAuthorSelection(value);
const blurAuthor = (event) =>
  props.mobile ? handleMobileAuthorBlur(event) : handleAuthorBlur(event);
</script>

<style scoped>
@import "./styles/search-field-labels.css";
.filters-section {
  background: var(--color-surface-0);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  border: 1px solid var(--color-surface-1);
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-label {
  color: var(--color-text-muted) !important;
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 4px;
}

.filter-input :deep(.v-field) {
  background-color: var(--color-surface-1) !important;
  border-radius: 6px;
}

.filter-input :deep(.v-field__input) {
  color: var(--color-text) !important;
  font-size: 0.9rem;
}

.filter-input :deep(.v-field__outline) {
  border-color: var(--color-surface-2) !important;
}

.filter-input :deep(.v-field--focused .v-field__outline) {
  border-color: var(--color-blue) !important;
}

.date-range-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-input {
  flex: 1;
  min-width: 0;
}

.date-range-container :deep(.date-filter-field) {
  min-width: 0;
}

.date-range-container :deep(.v-field__input) {
  min-width: 120px;
}

.date-input :deep(.v-field) {
  background-color: var(--color-surface-1) !important;
  border-radius: 6px;
}

.date-input :deep(.v-field__input) {
  color: var(--color-text) !important;
  font-size: 0.9rem;
}

.date-separator {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  white-space: nowrap;
}

@media (max-width: 600px) {
  .filters-section {
    padding: 10px;
  }

  .date-range-container {
    flex-direction: column;
    align-items: stretch;
  }

  .date-separator {
    text-align: center;
    padding: 4px 0;
  }
}

.filters-section {
  background: var(--color-surface-0);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  border: 1px solid var(--color-surface-1);
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  color: var(--color-text-muted) !important;
  font-size: 0.9rem;
  font-weight: 500;
}

.date-range-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.date-input {
  flex: 1;
}

.date-input :deep(.v-field) {
  background-color: var(--color-surface-1) !important;
  border-radius: 8px;
  min-height: 40px !important;
}

.date-input :deep(.v-field__input) {
  color: var(--color-text) !important;
  padding-left: 12px !important;
  padding-right: 40px !important; /* 为日期图标留出空间 */
}

.date-input :deep(.v-field__outline) {
  border-color: var(--color-surface-2) !important;
}

.date-input :deep(.v-field--focused .v-field__outline) {
  border-color: var(--color-blue) !important;
}

.date-separator {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  white-space: nowrap;
}

@media (max-width: 600px) {
  .filters-section {
    padding: 16px;
  }

  .date-range-container {
    flex-direction: column;
    align-items: stretch;
  }

  .date-separator {
    text-align: center;
    padding: 8px 0;
  }
}

.mobile-filters {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 24px;
}

.mobile-filter-title {
  color: var(--color-text);
  font-size: 1.1rem;
  font-weight: 500;
  margin-bottom: 16px;
  font-family: "JetBrains Mono", monospace;
}

.mobile-filter-input {
  width: 100%;
}

.mobile-date-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.mobile-date-input {
  min-width: 0;
}
</style>
