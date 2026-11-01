<script setup>
import { useMemeWidget } from "@/composables/useMemeWidget.js";

const images = Object.values(
  import.meta.glob(
    ["../../assets/meme/*.[gG][iI][fF]", "../../assets/meme/*.webp"],
    {
      eager: true,
      query: "?url",
      import: "default",
    },
  ),
);
const { visible, autoRotate, current, imageFailed, randomize } =
  useMemeWidget(images);
</script>

<template>
  <aside
    class="meme-widget"
    :class="{ 'meme-widget-closed': !visible }"
    aria-label="Meme 挂件"
  >
    <template v-if="visible">
      <div class="meme-display">
        <img
          v-if="current"
          :key="current"
          :src="current"
          alt="Meme 动画"
          @error="imageFailed"
        />
        <p v-else role="status">暂无可用动画</p>
      </div>
    </template>
    <div class="meme-controls">
      <button
        v-if="visible"
        type="button"
        aria-label="随机换图"
        title="随机换图"
        :disabled="!current"
        @click="randomize"
      >
        <v-icon icon="mdi-shuffle-variant" size="18" aria-hidden="true" />
      </button>
      <button
        v-if="visible"
        type="button"
        aria-label="自动轮换"
        :title="autoRotate ? '关闭自动轮换' : '开启自动轮换'"
        :aria-pressed="autoRotate"
        @click="autoRotate = !autoRotate"
      >
        <v-icon icon="mdi-autorenew" size="18" aria-hidden="true" />
      </button>
      <button
        type="button"
        :aria-label="visible ? '关闭 Meme' : '显示 Meme'"
        :title="visible ? '关闭 Meme' : '显示 Meme'"
        :aria-pressed="visible"
        @click="visible = !visible"
      >
        <v-icon icon="mdi-power" size="18" aria-hidden="true" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.meme-widget {
  position: fixed;
  left: max(20px, env(safe-area-inset-left));
  bottom: max(20px, env(safe-area-inset-bottom));
  width: 200px;
  z-index: 999;
}
.meme-display {
  height: 200px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.meme-display img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.meme-display p {
  color: var(--color-text);
  background: var(--color-base);
  padding: 8px;
}
.meme-controls {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 6px;
}
.meme-widget button {
  color: var(--color-text);
  background: var(--color-surface-0);
  border: 1px solid var(--color-surface-2);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px var(--color-black-20);
  transition:
    color 0.15s,
    background 0.15s;
  cursor: pointer;
}
.meme-widget button:hover:not(:disabled),
.meme-widget button[aria-pressed="true"] {
  background: var(--color-surface-1);
  color: var(--color-mauve);
}
.meme-widget button:disabled {
  opacity: 0.4;
  cursor: default;
}
.meme-widget button:focus-visible {
  outline: 2px solid var(--color-mauve);
  outline-offset: 2px;
}
@media (max-width: 768px) {
  .meme-widget {
    width: 140px;
    left: max(12px, env(safe-area-inset-left));
    bottom: max(16px, env(safe-area-inset-bottom));
  }
  .meme-display {
    height: 140px;
  }
}
.meme-widget-closed {
  width: 32px;
  left: max(8px, env(safe-area-inset-left));
  bottom: max(8px, env(safe-area-inset-bottom));
}
.meme-widget-closed .meme-controls {
  margin-top: 0;
}
</style>
