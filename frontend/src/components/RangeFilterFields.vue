<template>
  <div class="range-filter" :class="{ 'range-filter-flat': flat }">
    <div class="range-label">{{ label }}</div>
    <v-range-slider
      v-model="sliderValue"
      :min="0"
      :max="sliderCoordinateMax"
      :step="sliderCoordinateStep"
      color="var(--color-mauve)"
      hide-details
      class="range-slider"
    />
    <div class="range-inputs">
      <v-text-field
        :model-value="displayMin"
        type="number"
        min="0"
        :step="displayStep"
        label="最小"
        :suffix="unit"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        @update:model-value="updateMin"
      />
      <span>至</span>
      <v-text-field
        :model-value="displayMax"
        type="number"
        min="0"
        :step="displayStep"
        label="最大"
        :suffix="unit"
        density="compact"
        variant="outlined"
        hide-details
        clearable
        @update:model-value="updateMax"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  label: { type: String, required: true },
  minValue: { type: Number, default: null },
  maxValue: { type: Number, default: null },
  sliderMax: { type: Number, required: true },
  step: { type: Number, default: 1 },
  scale: { type: Number, default: 1 },
  unit: { type: String, default: "" },
  flat: { type: Boolean, default: false },
  nonlinearDuration: { type: Boolean, default: false },
});

const emit = defineEmits(["update:minValue", "update:maxValue"]);

const effectiveMax = computed(() => {
  const rawMax = Math.max(
    props.sliderMax,
    props.minValue || 0,
    props.maxValue || 0,
    props.step,
  );
  return Math.ceil(rawMax / props.step) * props.step;
});
const sliderCoordinateMax = computed(() =>
  props.nonlinearDuration && effectiveMax.value > 600 ? 100 : effectiveMax.value,
);
const sliderCoordinateStep = computed(() =>
  props.nonlinearDuration && effectiveMax.value > 600 ? 1 : props.step,
);
const toSliderPosition = (value) => {
  if (!props.nonlinearDuration || effectiveMax.value <= 600) {
    return (value / effectiveMax.value) * sliderCoordinateMax.value;
  }
  if (value <= 600) return (value / 600) * 50;
  return 50 + ((value - 600) / (effectiveMax.value - 600)) * 50;
};
const fromSliderPosition = (position) => {
  if (!props.nonlinearDuration || effectiveMax.value <= 600) {
    return position / sliderCoordinateMax.value * effectiveMax.value;
  }
  if (position <= 50) return (position / 50) * 600;
  return 600 + ((position - 50) / 50) * (effectiveMax.value - 600);
};
const snapValue = (value) =>
  Math.min(
    effectiveMax.value,
    Math.max(0, Math.round(value / props.step) * props.step),
  );
const displayMin = computed(() =>
  props.minValue === null ? null : props.minValue / props.scale,
);
const displayMax = computed(() =>
  props.maxValue === null ? null : props.maxValue / props.scale,
);
const displayStep = computed(() => props.step / props.scale);

const sliderValue = computed({
  get: () => [
    toSliderPosition(props.minValue ?? 0),
    toSliderPosition(props.maxValue ?? effectiveMax.value),
  ],
  set: ([min, max]) => {
    emit("update:minValue", snapValue(fromSliderPosition(min)));
    emit("update:maxValue", snapValue(fromSliderPosition(max)));
  },
});

const parseDisplayValue = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed * props.scale : null;
};
const updateMin = (value) => emit("update:minValue", parseDisplayValue(value));
const updateMax = (value) => emit("update:maxValue", parseDisplayValue(value));
</script>

<style scoped>
.range-filter {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: var(--color-surface-0);
  border: 1px solid var(--color-surface-1);
  border-radius: 10px;
}
.range-filter-flat {
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
}
.range-label {
  color: var(--color-yellow);
  font-size: 0.82rem;
  font-weight: 600;
}
.range-slider {
  margin: 0 4px;
  color: var(--color-mauve);
}
.range-slider :deep(.v-slider-track__background) {
  background: var(--color-surface-2) !important;
  opacity: 1;
}
.range-slider :deep(.v-slider-thumb__surface) {
  box-shadow: 0 0 0 3px var(--color-mauve-20);
}
.range-inputs {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
}
.range-inputs > span {
  color: var(--color-text-muted);
}
.range-inputs :deep(.v-field) {
  color: var(--color-text) !important;
  background: var(--color-surface-1) !important;
  border-radius: 8px;
}
.range-inputs :deep(.v-field__input),
.range-inputs :deep(.v-label),
.range-inputs :deep(input) {
  color: var(--color-text) !important;
}
.range-inputs :deep(.v-field__outline) {
  color: var(--color-surface-2) !important;
}
.range-inputs :deep(.v-field--focused .v-field__outline) {
  color: var(--color-mauve) !important;
}
.range-inputs :deep(.v-field__suffix),
.range-inputs :deep(.v-field__clearable) {
  color: var(--color-text-muted) !important;
}
</style>
