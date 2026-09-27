<template>
  <v-menu
    v-model="open"
    :close-on-content-click="false"
    location="bottom end"
    :offset="8"
    :transition="false"
    @update:model-value="handleOpen"
  >
    <template #activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        class="sort-btn filter-btn"
        :class="{ active: activeCount > 0 }"
        size="small"
        rounded="lg"
        :ripple="false"
      >
        <v-icon size="16">mdi-filter-variant</v-icon>
        <span>筛选</span>
        <span v-if="activeCount" class="filter-count">{{ activeCount }}</span>
      </v-btn>
    </template>

    <v-card class="filter-card" @click.stop>
      <v-card-title>自定义筛选</v-card-title>
      <v-card-text class="filter-content">
        <template v-if="mode === 'authors'">
          <RangeFilterFields
            label="视频数量"
            :min-value="draft.minWorks"
            :max-value="draft.maxWorks"
            :slider-max="Math.max(maxWorks, 1)"
            unit="个"
            @update:min-value="draft.minWorks = $event"
            @update:max-value="draft.maxWorks = $event"
          />
          <RangeFilterFields
            label="平均视频时长"
            :min-value="draft.minAverageDuration"
            :max-value="draft.maxAverageDuration"
            :slider-max="Math.max(maxDuration, 1800)"
            :step="60"
            :scale="60"
            unit="分钟"
            @update:min-value="draft.minAverageDuration = $event"
            @update:max-value="draft.maxAverageDuration = $event"
          />
        </template>

        <template v-else>
          <RangeFilterFields
            label="视频时长"
            :min-value="draft.minDuration"
            :max-value="draft.maxDuration"
            :slider-max="Math.max(maxDuration, 1800)"
            :step="60"
            :scale="60"
            unit="分钟"
            @update:min-value="draft.minDuration = $event"
            @update:max-value="draft.maxDuration = $event"
          />
          <v-select
            v-model="draft.translationStatus"
            :items="translationOptions"
            item-title="title"
            item-value="value"
            label="翻译状态"
            variant="outlined"
            density="compact"
            hide-details
            :menu-props="{ contentClass: 'filter-select-menu' }"
          />
          <div class="date-fields">
            <DateFilterField v-model="draft.dateFrom" label="开始日期" />
            <DateFilterField v-model="draft.dateTo" label="结束日期" />
          </div>
        </template>

        <v-switch
          v-model="draft.includeUnknownDuration"
          label="包含未知时长"
          :disabled="!durationActive"
          color="var(--color-mauve)"
          density="compact"
          hide-details
        />
        <div v-if="!valid" class="filter-error">最小值不能大于最大值</div>
      </v-card-text>
      <v-card-actions>
        <v-btn class="reset-filter-btn" variant="text" :ripple="false" @click="reset">重置</v-btn>
        <v-spacer />
        <v-btn class="apply-filter-btn" variant="flat" :ripple="false" :disabled="!valid" @click="apply">应用筛选</v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import RangeFilterFields from "./RangeFilterFields.vue";
import DateFilterField from "./DateFilterField.vue";

const props = defineProps({
  mode: { type: String, required: true, validator: (v) => ["authors", "videos"].includes(v) },
  modelValue: { type: Object, required: true },
  maxWorks: { type: Number, default: 1 },
  maxDuration: { type: Number, default: 1800 },
  activeCount: { type: Number, default: 0 },
});
const emit = defineEmits(["apply"]);
const open = ref(false);
const draft = reactive({});
const translationOptions = [
  { title: "全部", value: "all" },
  { title: "中文内嵌", value: "1" },
  { title: "CC字幕", value: "2" },
  { title: "弹幕翻译", value: "3" },
  { title: "无需翻译", value: "4" },
  { title: "暂无翻译", value: "5" },
];

const defaults = () =>
  props.mode === "authors"
    ? { minWorks: null, maxWorks: null, minAverageDuration: null, maxAverageDuration: null, includeUnknownDuration: false }
    : { minDuration: null, maxDuration: null, translationStatus: "all", dateFrom: "", dateTo: "", includeUnknownDuration: false };
const copyIntoDraft = (source) => Object.assign(draft, defaults(), source);
const handleOpen = (value) => { if (value) copyIntoDraft(props.modelValue); };
const validRange = (min, max) => min === null || max === null || min <= max;
const valid = computed(() =>
  props.mode === "authors"
    ? validRange(draft.minWorks, draft.maxWorks) && validRange(draft.minAverageDuration, draft.maxAverageDuration)
    : validRange(draft.minDuration, draft.maxDuration),
);
const durationActive = computed(() =>
  props.mode === "authors"
    ? draft.minAverageDuration !== null || draft.maxAverageDuration !== null
    : draft.minDuration !== null || draft.maxDuration !== null,
);
const apply = () => {
  const filters = { ...draft };
  if (!durationActive.value) filters.includeUnknownDuration = false;
  emit("apply", filters);
  open.value = false;
};
const reset = () => { emit("apply", defaults()); open.value = false; };
</script>

<style scoped>
@import "@/styles/SortControls.css";
.filter-card {
  width: min(420px, calc(100vw - 24px));
  overflow: hidden;
  color: var(--color-text) !important;
  background: var(--color-base) !important;
  border: 1px solid var(--color-surface-2);
  border-radius: 14px !important;
  box-shadow: 0 12px 36px var(--color-deep-shadow-65) !important;
  font-family: "JetBrains Mono", "JetBrainsMono Nerd Font", monospace;
}
.filter-card :deep(.v-card-title) {
  padding: 16px 18px 12px;
  color: var(--color-yellow);
  font-size: 1rem;
  font-weight: 700;
  border-bottom: 1px solid var(--color-surface-1);
}
.filter-content { display: flex; flex-direction: column; gap: 14px; padding: 16px 18px 10px !important; }
.filter-content :deep(.v-field) {
  color: var(--color-text) !important;
  background: var(--color-surface-0) !important;
  border-radius: 8px;
}
.filter-content :deep(.v-field__input),
.filter-content :deep(.v-label),
.filter-content :deep(input) { color: var(--color-text) !important; }
.filter-content :deep(.v-field__outline) { color: var(--color-surface-2) !important; }
.filter-content :deep(.v-field--focused .v-field__outline) { color: var(--color-mauve) !important; }
.filter-content :deep(.v-input__append),
.filter-content :deep(.v-field__append-inner),
.filter-content :deep(.v-field__clearable) { color: var(--color-text-muted) !important; }
.filter-content :deep(.v-switch .v-selection-control__input) { color: var(--color-mauve) !important; }
.filter-card :deep(.v-card-actions) { padding: 10px 14px 14px; border-top: 1px solid var(--color-surface-1); }
.filter-card :deep(.v-ripple__container) { display: none !important; }
.date-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.filter-count { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; display: inline-flex; align-items: center; justify-content: center; background: var(--color-base); color: var(--color-mauve); font-size: 0.7rem !important; }
.filter-error { color: var(--color-red); font-size: 0.8rem; }
.reset-filter-btn { color: var(--color-text-muted) !important; }
.reset-filter-btn:hover { color: var(--color-red) !important; background: var(--color-red-12) !important; }
.apply-filter-btn { color: var(--color-base) !important; background: var(--color-mauve) !important; font-weight: 700; }
.apply-filter-btn:hover { background: var(--color-lavender) !important; }
:global(.filter-select-menu .v-list) { color: var(--color-text); background: var(--color-surface-0); border: 1px solid var(--color-surface-2); }
:global(.filter-select-menu .v-list-item:hover) { background: var(--color-mauve-14); }
:global(.filter-select-menu .v-list-item--active) { color: var(--color-mauve); background: var(--color-mauve-20); }
@media (max-width: 480px) { .date-fields { grid-template-columns: 1fr; } }
</style>
