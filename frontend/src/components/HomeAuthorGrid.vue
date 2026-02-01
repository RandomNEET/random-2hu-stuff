<template>
  <div class="card-grid">
    <HomeAuthorCard
      v-for="author in authors"
      :key="author.id"
      :author="author"
    />
  </div>
</template>

<script setup>
import HomeAuthorCard from './HomeAuthorCard.vue';

const props = defineProps({
  authors: {
    type: Array,
    required: true
  }
});
</script>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
  padding: 24px;
  background-color: #1e1e2e;
  /* Catppuccin Mocha Base */
  justify-content: center;
}

/* Responsive grid layout */
@media (min-width: 1600px) {
  /* 4K large screen: 7-9 per row */
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    max-width: 2200px;
    margin: 0 auto;
  }
}

@media (min-width: 1200px) and (max-width: 1599px) {
  /* Medium desktop: 5-6 per row */
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    max-width: 1400px;
    margin: 0 auto;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  /* Small desktop/tablet: 4 per row */
  .card-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    padding: 20px;
  }
}

@media (min-width: 481px) and (max-width: 767px) {
  /* Large mobile/small tablet: 3 per row */
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding: 16px;
  }
}

@media (max-width: 480px) {
  /* Mobile: 2 per row */
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    padding: 12px;
  }
}

/* Add staggered animation delay for different cards - play by row, max 8 rows */
.card-grid :deep(.card-item) {
  animation-delay: 0s; /* Default delay */
}

/* Mobile: 2 per row, max 8 rows */
@media (max-width: 480px) {
  .card-grid :deep(.card-item:nth-child(1)),
  .card-grid :deep(.card-item:nth-child(2)) {
    animation-delay: 0s;
  }
  .card-grid :deep(.card-item:nth-child(3)),
  .card-grid :deep(.card-item:nth-child(4)) {
    animation-delay: 0.1s;
  }
  .card-grid :deep(.card-item:nth-child(5)),
  .card-grid :deep(.card-item:nth-child(6)) {
    animation-delay: 0.2s;
  }
  .card-grid :deep(.card-item:nth-child(7)),
  .card-grid :deep(.card-item:nth-child(8)) {
    animation-delay: 0.3s;
  }
  .card-grid :deep(.card-item:nth-child(9)),
  .card-grid :deep(.card-item:nth-child(10)) {
    animation-delay: 0.4s;
  }
  .card-grid :deep(.card-item:nth-child(11)),
  .card-grid :deep(.card-item:nth-child(12)) {
    animation-delay: 0.5s;
  }
  .card-grid :deep(.card-item:nth-child(13)),
  .card-grid :deep(.card-item:nth-child(14)) {
    animation-delay: 0.6s;
  }
  .card-grid :deep(.card-item:nth-child(15)),
  .card-grid :deep(.card-item:nth-child(16)) {
    animation-delay: 0.7s;
  }
}

/* Large mobile/small tablet: 3 per row, max 8 rows */
@media (min-width: 481px) and (max-width: 767px) {
  .card-grid :deep(.card-item:nth-child(1)),
  .card-grid :deep(.card-item:nth-child(2)),
  .card-grid :deep(.card-item:nth-child(3)) {
    animation-delay: 0s;
  }
  .card-grid :deep(.card-item:nth-child(4)),
  .card-grid :deep(.card-item:nth-child(5)),
  .card-grid :deep(.card-item:nth-child(6)) {
    animation-delay: 0.1s;
  }
  .card-grid :deep(.card-item:nth-child(7)),
  .card-grid :deep(.card-item:nth-child(8)),
  .card-grid :deep(.card-item:nth-child(9)) {
    animation-delay: 0.2s;
  }
  .card-grid :deep(.card-item:nth-child(10)),
  .card-grid :deep(.card-item:nth-child(11)),
  .card-grid :deep(.card-item:nth-child(12)) {
    animation-delay: 0.3s;
  }
  .card-grid :deep(.card-item:nth-child(13)),
  .card-grid :deep(.card-item:nth-child(14)),
  .card-grid :deep(.card-item:nth-child(15)) {
    animation-delay: 0.4s;
  }
  .card-grid :deep(.card-item:nth-child(16)),
  .card-grid :deep(.card-item:nth-child(17)),
  .card-grid :deep(.card-item:nth-child(18)) {
    animation-delay: 0.5s;
  }
  .card-grid :deep(.card-item:nth-child(19)),
  .card-grid :deep(.card-item:nth-child(20)),
  .card-grid :deep(.card-item:nth-child(21)) {
    animation-delay: 0.6s;
  }
  .card-grid :deep(.card-item:nth-child(22)),
  .card-grid :deep(.card-item:nth-child(23)),
  .card-grid :deep(.card-item:nth-child(24)) {
    animation-delay: 0.7s;
  }
}

/* Small desktop/tablet: 4 per row, max 8 rows */
@media (min-width: 768px) and (max-width: 1199px) {
  .card-grid :deep(.card-item:nth-child(1)),
  .card-grid :deep(.card-item:nth-child(2)),
  .card-grid :deep(.card-item:nth-child(3)),
  .card-grid :deep(.card-item:nth-child(4)) {
    animation-delay: 0s;
  }
  .card-grid :deep(.card-item:nth-child(5)),
  .card-grid :deep(.card-item:nth-child(6)),
  .card-grid :deep(.card-item:nth-child(7)),
  .card-grid :deep(.card-item:nth-child(8)) {
    animation-delay: 0.1s;
  }
  .card-grid :deep(.card-item:nth-child(9)),
  .card-grid :deep(.card-item:nth-child(10)),
  .card-grid :deep(.card-item:nth-child(11)),
  .card-grid :deep(.card-item:nth-child(12)) {
    animation-delay: 0.2s;
  }
  .card-grid :deep(.card-item:nth-child(13)),
  .card-grid :deep(.card-item:nth-child(14)),
  .card-grid :deep(.card-item:nth-child(15)),
  .card-grid :deep(.card-item:nth-child(16)) {
    animation-delay: 0.3s;
  }
  .card-grid :deep(.card-item:nth-child(17)),
  .card-grid :deep(.card-item:nth-child(18)),
  .card-grid :deep(.card-item:nth-child(19)),
  .card-grid :deep(.card-item:nth-child(20)) {
    animation-delay: 0.4s;
  }
  .card-grid :deep(.card-item:nth-child(21)),
  .card-grid :deep(.card-item:nth-child(22)),
  .card-grid :deep(.card-item:nth-child(23)),
  .card-grid :deep(.card-item:nth-child(24)) {
    animation-delay: 0.5s;
  }
  .card-grid :deep(.card-item:nth-child(25)),
  .card-grid :deep(.card-item:nth-child(26)),
  .card-grid :deep(.card-item:nth-child(27)),
  .card-grid :deep(.card-item:nth-child(28)) {
    animation-delay: 0.6s;
  }
  .card-grid :deep(.card-item:nth-child(29)),
  .card-grid :deep(.card-item:nth-child(30)),
  .card-grid :deep(.card-item:nth-child(31)),
  .card-grid :deep(.card-item:nth-child(32)) {
    animation-delay: 0.7s;
  }
}

/* Medium desktop: dynamic per row count, max 8 rows */
@media (min-width: 1200px) and (max-width: 1599px) {
  .card-grid :deep(.card-item:nth-child(-n + 6)) {
    animation-delay: 0s;
  } /* Row 1: assume 6 per row */
  .card-grid :deep(.card-item:nth-child(n + 7):nth-child(-n + 12)) {
    animation-delay: 0.1s;
  } /* Row 2 */
  .card-grid :deep(.card-item:nth-child(n + 13):nth-child(-n + 18)) {
    animation-delay: 0.2s;
  } /* Row 3 */
  .card-grid :deep(.card-item:nth-child(n + 19):nth-child(-n + 24)) {
    animation-delay: 0.3s;
  } /* Row 4 */
  .card-grid :deep(.card-item:nth-child(n + 25):nth-child(-n + 30)) {
    animation-delay: 0.4s;
  } /* Row 5 */
  .card-grid :deep(.card-item:nth-child(n + 31):nth-child(-n + 36)) {
    animation-delay: 0.5s;
  } /* Row 6 */
  .card-grid :deep(.card-item:nth-child(n + 37):nth-child(-n + 42)) {
    animation-delay: 0.6s;
  } /* Row 7 */
  .card-grid :deep(.card-item:nth-child(n + 43):nth-child(-n + 48)) {
    animation-delay: 0.7s;
  } /* Row 8 */
}

/* 4K large screen: dynamic per row count, max 8 rows */
@media (min-width: 1600px) {
  .card-grid :deep(.card-item:nth-child(-n + 8)) {
    animation-delay: 0s;
  } /* Row 1: assume 8 per row */
  .card-grid :deep(.card-item:nth-child(n + 9):nth-child(-n + 16)) {
    animation-delay: 0.1s;
  } /* Row 2 */
  .card-grid :deep(.card-item:nth-child(n + 17):nth-child(-n + 24)) {
    animation-delay: 0.2s;
  } /* Row 3 */
  .card-grid :deep(.card-item:nth-child(n + 25):nth-child(-n + 32)) {
    animation-delay: 0.3s;
  } /* Row 4 */
  .card-grid :deep(.card-item:nth-child(n + 33):nth-child(-n + 40)) {
    animation-delay: 0.4s;
  } /* Row 5 */
  .card-grid :deep(.card-item:nth-child(n + 41):nth-child(-n + 48)) {
    animation-delay: 0.5s;
  } /* Row 6 */
  .card-grid :deep(.card-item:nth-child(n + 49):nth-child(-n + 56)) {
    animation-delay: 0.6s;
  } /* Row 7 */
  .card-grid :deep(.card-item:nth-child(n + 57):nth-child(-n + 64)) {
    animation-delay: 0.7s;
  } /* Row 8 */
}
</style>
