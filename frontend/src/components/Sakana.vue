<template>
  <div ref="sakanaElement" class="sakana-container"></div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import SakanaWidget from "sakana-widget";
import "sakana-widget/lib/index.css";

import kaguyaImg from "@/assets/kaguya.png";
import mokouImg from "@/assets/mokou.png";

const sakanaElement = ref(null);

onMounted(() => {
  if (!sakanaElement.value) return;

  try {
    const baseConfig = SakanaWidget.getCharacter("chisato");

    const kaguya = {
      ...baseConfig,
      image: kaguyaImg,
    };

    const mokou = {
      ...baseConfig,
      image: mokouImg,
    };

    SakanaWidget.registerCharacter("chisato", kaguya);
    SakanaWidget.registerCharacter("takina", mokou);

    const widget = new SakanaWidget({
      character: "chisato",
      autoFit: true,
      controls: true,
    }).mount(sakanaElement.value);

    widget.triggerAutoMode();
  } catch (error) {
    console.error("SakanaWidget 初始化失败:", error);
  }
});
</script>

<style scoped>
.sakana-container {
  position: fixed;
  left: 20px;
  bottom: 20px;
  width: 200px;
  height: 200px;
  z-index: 999;
}
.sakana-container .sakana-icon-github {
  display: none !important;
}
</style>
