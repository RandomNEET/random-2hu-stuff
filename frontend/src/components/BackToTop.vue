<template>
  <v-btn
    v-if="show"
    icon
    size="large"
    class="back-to-top-btn"
    @click="scrollToTop"
    style="position: fixed; bottom: 24px; right: 24px; z-index: 1000"
  >
    <v-icon>mdi-chevron-up</v-icon>
  </v-btn>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const show = ref(false);

const scrollToTop = () => {
  window.scrollTo({
    top: 0,
    behavior: 'smooth',
  });
};

const handleScroll = () => {
  show.value = window.scrollY > 300;
};

onMounted(() => {
  window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<style scoped>
/* BackToTop button styles are imported globally via @/styles/BackToTop.css */
@import '@/styles/BackToTop.css';
</style>
