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
          本网站主要收录群友推荐的东方相关二创视频，同时整理对应的出处
        </p>
        <p class="section-text" style="margin-top: 16px">
          因为作者头像和视频封面来自原频道，裸连时大部分图片可能无法正常加载，推荐使用代理访问以获得最佳体验
        </p>
      </div>

      <!-- APP section -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-android</v-icon>
          <h2 class="section-title">APP</h2>
        </div>
        <div
          style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap"
        >
          <p class="section-text" style="font-weight: 500; margin: 0">
            APK下载地址：
          </p>
          <v-btn
            variant="outlined"
            color="primary"
            prepend-icon="mdi-github"
            href="https://github.com/RandomNEET/random-2hu-stuff/releases/tag/apk-1.1.0"
            target="_blank"
            size="large"
          >
            GitHub
          </v-btn>
          <v-btn
            variant="outlined"
            color="primary"
            prepend-icon="mdi-cloud-download"
            href="https://pan.quark.cn/s/38b9ff61dde3"
            target="_blank"
            size="large"
          >
            夸克网盘 提取码：H2gm
          </v-btn>
        </div>
      </div>

      <!-- Contact section -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-account-group</v-icon>
          <h2 class="section-title">参与收录整理</h2>
        </div>
        <div
          style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap"
        >
          <p class="section-text" style="margin: 0">
            如果你也有想要推荐的作品，欢迎加入一起整理收录！
          </p>
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
        <SiteStatistics />
      </div>
    </div>
  </div>
</template>

<script setup>
import SiteStatistics from "@/components/about/SiteStatistics.vue";
</script>

<style scoped>
.about-page {
  min-height: 100vh;
  background: linear-gradient(
    135deg,
    var(--color-base) 0%,
    var(--color-crust) 100%
  ); /* Catppuccin Mocha Base to Crust gradient */
  color: var(--color-text); /* Catppuccin Mocha Text */
  padding: 32px 0;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
.page-header {
  text-align: center;
  margin-bottom: 48px;
  padding: 32px 0;
}
.header-icon {
  color: var(--color-yellow); /* Catppuccin Mocha Yellow */
  margin-bottom: 16px;
}
.page-title {
  font-size: 3rem;
  font-weight: bold;
  color: var(--color-yellow); /* Catppuccin Mocha Yellow */
  margin-bottom: 8px;
  text-shadow: 0 2px 8px var(--color-yellow-30); /* Subtle glow effect */
}
.page-subtitle {
  font-size: 1.2rem;
  color: var(--color-text-muted); /* Catppuccin Mocha Subtext0 */
  margin: 0;
}
.about-section {
  background: var(--color-surface-0-40); /* Semi-transparent Surface0 */
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid var(--color-mauve-20); /* Subtle Mauve border */
  backdrop-filter: blur(10px); /* Glassmorphism blur effect */
}
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--color-mauve-30); /* Mauve accent line */
}
.section-icon {
  color: var(--color-mauve); /* Catppuccin Mocha Mauve */
  font-size: 28px;
}
.section-title {
  color: var(--color-mauve); /* Catppuccin Mocha Mauve */
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0;
}
.section-text {
  color: var(--color-text); /* Catppuccin Mocha Text */
  font-size: 1.1rem;
  line-height: 1.6; /* Improved readability */
  margin: 0;
}
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
}
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
