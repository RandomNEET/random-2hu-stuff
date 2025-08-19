<template>
  <div class="about-page">
    <div class="container">
      <!-- Page title section -->
      <div class="page-header">
        <v-icon size="48" class="header-icon">mdi-information</v-icon>
        <h1 class="page-title">关于 random 2hu stuff</h1>
      </div>

      <!-- Introduction section -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-book-open-variant</v-icon>
          <h2 class="section-title">简介</h2>
        </div>
        <p class="section-text">
          本网站主要收录组员寻思好看并大力推荐的东方相关二创视频，同时整理对应的出处。
        </p>
        <p class="section-text" style="margin-top: 16px">
          PS：因为作者头像和视频封面来自原频道，裸连时大部分图片可能无法正常加载，推荐使用代理访问以获得最佳体验。
        </p>
      </div>

      <!-- Collaborative maintenance section -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-account-group</v-icon>
          <h2 class="section-title">共同维护</h2>
        </div>
        <p class="section-text">
          如果你也有想要推荐的作品，欢迎加入一起维护网站！
        </p>
        <p class="section-text" style="margin-top: 16px">
          PS：会复制粘贴就行了，没有技术要求。
        </p>
        <div class="group-link" style="margin-top: 20px; text-align: center">
          <v-btn
            variant="outlined"
            color="primary"
            prepend-icon="mdi-account-group"
            href="https://qm.qq.com/q/NuSbWCMd8"
            target="_blank"
            size="large"
          >
            QQ群：976462503
          </v-btn>
        </div>
      </div>

      <!-- Statistics section -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-chart-bar</v-icon>
          <h2 class="section-title">数据统计</h2>
        </div>
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { API_URLS } from "@/config/api.js";

// Reactive data for statistics
const totalAuthors = ref(0);
const totalVideos = ref(0);
const translatedVideos = ref(0);

// Fetch statistics data from API
const fetchStats = async () => {
  try {
    // Use stats API to get accurate data
    const statsRes = await fetch(API_URLS.STATS);
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
/* Main about page container with gradient background */
.about-page {
  min-height: 100vh;
  background: linear-gradient(
    135deg,
    #1e1e2e 0%,
    #181825 100%
  ); /* Catppuccin Mocha Base to Crust gradient */
  color: #cdd6f4; /* Catppuccin Mocha Text */
  padding: 32px 0;
}

/* Content container with responsive width */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Page header section styling */
.page-header {
  text-align: center;
  margin-bottom: 48px;
  padding: 32px 0;
}

.header-icon {
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  margin-bottom: 16px;
}

.page-title {
  font-size: 3rem;
  font-weight: bold;
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  margin-bottom: 8px;
  text-shadow: 0 2px 8px rgba(249, 226, 175, 0.3); /* Subtle glow effect */
}

.page-subtitle {
  font-size: 1.2rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  margin: 0;
}

/* About section cards with glassmorphism effect */
.about-section {
  background: rgba(49, 50, 68, 0.4); /* Semi-transparent Surface0 */
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid rgba(203, 166, 247, 0.2); /* Subtle Mauve border */
  backdrop-filter: blur(10px); /* Glassmorphism blur effect */
}

/* Section headers with icon and title */
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(203, 166, 247, 0.3); /* Mauve accent line */
}

.section-icon {
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  font-size: 28px;
}

.section-title {
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0;
}

.section-text {
  color: #cdd6f4; /* Catppuccin Mocha Text */
  font-size: 1.1rem;
  line-height: 1.6; /* Improved readability */
  margin: 0;
}

/* Statistics grid layout */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(200px, 1fr)
  ); /* Responsive grid */
  gap: 24px;
}

/* Individual statistics cards */
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: rgba(30, 30, 46, 0.6); /* Semi-transparent Base */
  border-radius: 12px;
  border: 1px solid rgba(137, 180, 250, 0.2); /* Blue border */
  transition: all 0.3s ease; /* Smooth hover transitions */
}

.stat-card:hover {
  background: rgba(30, 30, 46, 0.8); /* Darker on hover */
  border-color: rgba(137, 180, 250, 0.4); /* Brighter border on hover */
  transform: translateY(-2px); /* Subtle lift effect */
}

/* Statistics card content styling */
.stat-icon {
  color: #89b4fa; /* Catppuccin Mocha Blue */
  flex-shrink: 0; /* Prevent icon from shrinking */
}

.stat-content {
  flex: 1; /* Take remaining space */
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: #89b4fa; /* Catppuccin Mocha Blue */
  margin-bottom: 4px;
}

.stat-label {
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  font-size: 0.9rem;
  font-weight: 500;
}

/* Responsive design for mobile and tablet */
@media (max-width: 768px) {
  .container {
    padding: 0 16px; /* Reduced padding on mobile */
  }

  .page-title {
    font-size: 2rem; /* Smaller title on mobile */
  }

  .about-section {
    padding: 20px; /* Reduced section padding */
  }

  .stats-grid {
    grid-template-columns: 1fr; /* Single column on mobile */
  }

  .stat-card {
    justify-content: center; /* Center content on mobile */
    text-align: center;
  }
}

/* Extra small screen optimizations */
@media (max-width: 480px) {
  .about-page {
    padding: 16px 0; /* Minimal page padding */
  }

  .page-title {
    font-size: 1.5rem; /* Smallest title size */
  }

  .page-subtitle {
    font-size: 1rem;
  }

  .section-title {
    font-size: 1.4rem; /* Smaller section titles */
  }

  .about-section {
    padding: 16px; /* Minimal section padding */
    margin-bottom: 20px;
  }
}
</style>
