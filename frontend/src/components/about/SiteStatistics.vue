<template>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-icon">
        <v-icon size="32">mdi-account-group</v-icon>
      </div>
      <div class="stat-content">
        <div class="stat-number">{{ totalAuthors }}</div>
        <div class="stat-label">作者数量</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">
        <v-icon size="32">mdi-video-box</v-icon>
      </div>
      <div class="stat-content">
        <div class="stat-number">{{ totalVideos }}</div>
        <div class="stat-label">视频总数</div>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">
        <v-icon size="32">mdi-translate</v-icon>
      </div>
      <div class="stat-content">
        <div class="stat-number">{{ translatedVideos }}</div>
        <div class="stat-label">熟肉总数</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { fetchStats as fetchStatsResponse } from "@/services/api.js";

// Reactive data for statistics
const totalAuthors = ref(0);
const totalVideos = ref(0);
const translatedVideos = ref(0);

// Fetch statistics data from API
const fetchStats = async () => {
  try {
    // Use stats API to get accurate data
    const statsRes = await fetchStatsResponse();
    const stats = await statsRes.json();

    totalAuthors.value = stats.totalAuthors;
    totalVideos.value = stats.totalVideos;
    translatedVideos.value = stats.translatedVideos;
  } catch (error) {
    console.error("Failed to fetch statistics:", error);
    // Set default values on error
    totalAuthors.value = null;
    totalVideos.value = null;
    translatedVideos.value = null;
  }
};

// Initialize data on component mount
onMounted(() => {
  fetchStats();
});
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(200px, 1fr)
  ); /* Responsive grid */
  gap: 24px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: var(--color-base-60); /* Semi-transparent Base */
  border-radius: 12px;
  border: 1px solid var(--color-blue-20); /* Blue border */
  transition: all 0.3s ease; /* Smooth hover transitions */
}
.stat-card:hover {
  background: var(--color-base-80); /* Darker on hover */
  border-color: var(--color-blue-40); /* Brighter border on hover */
  transform: translateY(-2px); /* Subtle lift effect */
}
.stat-icon {
  color: var(--color-blue); /* Catppuccin Mocha Blue */
  flex-shrink: 0; /* Prevent icon from shrinking */
}
.stat-content {
  flex: 1; /* Take remaining space */
}
.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: var(--color-blue); /* Catppuccin Mocha Blue */
  margin-bottom: 4px;
}
.stat-label {
  color: var(--color-text-muted); /* Catppuccin Mocha Subtext0 */
  font-size: 0.9rem;
  font-weight: 500;
}
@media (max-width: 768px) {

  .stats-grid {
    grid-template-columns: 1fr; /* Single column on mobile */
  }

  .stat-card {
    justify-content: center; /* Center content on mobile */
    text-align: center;
  }
}
</style>
