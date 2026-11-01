import { computed, onMounted, onUnmounted, ref, watch } from "vue";

const STORAGE_KEY = "memeWidget-settings";

export function useMemeWidget(images) {
  let saved;
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
  } catch {
    // Storage may be unavailable or contain invalid JSON.
  }
  const visible = ref(
    typeof saved?.visible === "boolean" ? saved.visible : true,
  );
  const autoRotate = ref(
    typeof saved?.autoRotate === "boolean" ? saved.autoRotate : true,
  );
  const available = ref([...images]);
  const current = ref(null);
  const pageVisible = ref(true);
  const hasMultiple = computed(() => available.value.length > 1);
  let timer;

  function chooseNext() {
    const choices = available.value.filter((image) => image !== current.value);
    if (choices.length)
      current.value = choices[Math.floor(Math.random() * choices.length)];
    else current.value = available.value[0] ?? null;
  }

  function restartTimer() {
    clearTimeout(timer);
    timer = undefined;
    if (
      visible.value &&
      autoRotate.value &&
      pageVisible.value &&
      hasMultiple.value
    ) {
      const delay = 10000 + Math.floor(Math.random() * 50001);
      timer = setTimeout(() => {
        chooseNext();
        restartTimer();
      }, delay);
    }
  }

  function randomize() {
    chooseNext();
    restartTimer();
  }

  function imageFailed() {
    available.value = available.value.filter(
      (image) => image !== current.value,
    );
    chooseNext();
  }

  function visibilityChanged() {
    pageVisible.value = !document.hidden;
  }

  watch([visible, autoRotate], () => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          visible: visible.value,
          autoRotate: autoRotate.value,
        }),
      );
    } catch {
      // Keep the controls usable when storage is blocked.
    }
  });
  watch(visible, (enabled) => {
    if (enabled) chooseNext();
  });
  watch([visible, autoRotate, pageVisible, hasMultiple], restartTimer);
  chooseNext();
  onMounted(() => {
    visibilityChanged();
    document.addEventListener("visibilitychange", visibilityChanged);
    restartTimer();
  });
  onUnmounted(() => {
    clearTimeout(timer);
    document.removeEventListener("visibilitychange", visibilityChanged);
  });

  return { visible, autoRotate, current, imageFailed, randomize };
}
