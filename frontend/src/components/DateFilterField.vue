<template>
  <div class="date-filter-field">
    <v-text-field
      v-model="displayValue"
      :label="label"
      placeholder="年/月/日"
      inputmode="numeric"
      maxlength="10"
      variant="outlined"
      density="compact"
      hide-details="auto"
      clearable
      append-inner-icon="mdi-calendar-month"
      :error="invalid"
      :error-messages="invalid ? '请使用 年/月/日 格式' : ''"
      @blur="commit"
      @keyup.enter="commit"
      @click:clear="clear"
      @click:append-inner="openPicker"
    />
    <input
      ref="nativePicker"
      class="native-date-picker"
      type="date"
      :value="modelValue"
      tabindex="-1"
      aria-hidden="true"
      @change="selectDate"
    />
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  label: { type: String, required: true },
});
const emit = defineEmits(["update:modelValue"]);
const displayValue = ref("");
const invalid = ref(false);
const nativePicker = ref(null);

const toDisplay = (value) => (value ? value.replaceAll("-", "/") : "");
watch(
  () => props.modelValue,
  (value) => {
    displayValue.value = toDisplay(value);
    invalid.value = false;
  },
  { immediate: true },
);

const commit = () => {
  const value = displayValue.value?.trim();
  if (!value) {
    clear();
    return;
  }

  const match = value.match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})$/);
  if (!match) {
    invalid.value = true;
    return;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    invalid.value = true;
    return;
  }

  const iso = `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  displayValue.value = toDisplay(iso);
  invalid.value = false;
  emit("update:modelValue", iso);
};

const clear = () => {
  displayValue.value = "";
  invalid.value = false;
  emit("update:modelValue", "");
};

const openPicker = () => {
  const picker = nativePicker.value;
  if (!picker) return;
  if (typeof picker.showPicker === "function") picker.showPicker();
  else picker.click();
};

const selectDate = (event) => {
  const value = event.target.value;
  displayValue.value = toDisplay(value);
  invalid.value = false;
  emit("update:modelValue", value);
};
</script>

<style scoped>
.date-filter-field { position: relative; width: 100%; }
.native-date-picker { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
</style>
