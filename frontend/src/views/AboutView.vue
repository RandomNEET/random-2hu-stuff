<template>
  <div class="about-page">
    <div class="container">
      <!-- 页面标题 -->
      <div class="page-header">
        <v-icon size="48" class="header-icon">mdi-information</v-icon>
        <h1 class="page-title">关于 random 2hu stuff</h1>
      </div>

      <!-- 简介 -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-book-open-variant</v-icon>
          <h2 class="section-title">简介</h2>
        </div>
        <p class="section-text">
          本网站以作者为核心，系统性地收录每位MMD作者的全部作品，同时整理对应的转载视频，
          希望能提供一个完整、便捷的MMD系列视频浏览体验。PS：因为作者头像来自原频道，裸连的话应该是加载不出图片的，推荐使用代理访问以获得最佳体验。
        </p>
        <p class="section-text" style="margin-top: 16px;">
          由于网站目前只有我一个人在维护，转载视频的收集是最麻烦的部分<del> 首页刷到就顺手更新一下吧大概 </del>。
          如果发现有遗漏或未及时更新的情况，直接在评论区@我就好。
          如果希望增加对新作者的收录，或者对网站功能有任何建议，也欢迎直接私信告诉我。
        </p>
      </div>

      <!-- 联系方式 -->
      <div class="about-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-account-circle</v-icon>
          <h2 class="section-title">联系方式</h2>
        </div>
        <div class="contact-content">
          <div class="contact-links">
            <v-btn variant="outlined" color="pink" prepend-icon="mdi-play" href="https://space.bilibili.com/9217280"
              target="_blank" class="contact-btn">
              Bilibili
            </v-btn>
            <v-btn variant="outlined" color="green" prepend-icon="mdi-email" href="mailto:dev@randomneet.me"
              class="contact-btn">
              邮箱
            </v-btn>
            <v-btn variant="outlined" color="blue" prepend-icon="mdi-github" href="https://github.com/RandomNEET"
              target="_blank" class="contact-btn">
              GitHub
            </v-btn>
          </div>
        </div>
      </div>

      <!-- 数据统计 -->
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
import { ref, onMounted } from 'vue';
import { API_URLS } from '@/config/api.js';

const totalAuthors = ref(0);
const totalVideos = ref(0);
const translatedVideos = ref(0);

const fetchStats = async () => {
  try {
    // 使用统计API获取准确数据
    const statsRes = await fetch(API_URLS.STATS);
    const stats = await statsRes.json();
    
    totalAuthors.value = stats.totalAuthors;
    totalVideos.value = stats.totalVideos;
    translatedVideos.value = stats.translatedVideos;
  } catch (error) {
    console.error('获取统计数据失败:', error);
    // 设置默认值
    totalAuthors.value = null;
    totalVideos.value = null;
    translatedVideos.value = null;
  }
};

onMounted(() => {
  fetchStats();
});
</script>

<style scoped>
.about-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1e1e2e 0%, #181825 100%);
  color: #cdd6f4;
  padding: 32px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* 页面标题 */
.page-header {
  text-align: center;
  margin-bottom: 48px;
  padding: 32px 0;
}

.header-icon {
  color: #f9e2af;
  margin-bottom: 16px;
}

.page-title {
  font-size: 3rem;
  font-weight: bold;
  color: #f9e2af;
  margin-bottom: 8px;
  text-shadow: 0 2px 8px rgba(249, 226, 175, 0.3);
}

.page-subtitle {
  font-size: 1.2rem;
  color: #a6adc8;
  margin: 0;
}

/* 关于区块 */
.about-section {
  background: rgba(49, 50, 68, 0.4);
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid rgba(203, 166, 247, 0.2);
  backdrop-filter: blur(10px);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(203, 166, 247, 0.3);
}

.section-icon {
  color: #cba6f7;
  font-size: 28px;
}

.section-title {
  color: #cba6f7;
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0;
}

.section-text {
  color: #cdd6f4;
  font-size: 1.1rem;
  line-height: 1.6;
  margin: 0;
}

/* 联系方式 */
.contact-content {
  text-align: center;
}

.contact-links {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 20px;
}

.contact-btn {
  color: #89b4fa !important;
  border-color: #89b4fa !important;
}

.contact-btn:hover {
  background-color: rgba(137, 180, 250, 0.1) !important;
}

/* 统计数据 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: rgba(30, 30, 46, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(137, 180, 250, 0.2);
  transition: all 0.3s ease;
}

.stat-card:hover {
  background: rgba(30, 30, 46, 0.8);
  border-color: rgba(137, 180, 250, 0.4);
  transform: translateY(-2px);
}

.stat-icon {
  color: #89b4fa;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: #89b4fa;
  margin-bottom: 4px;
}

.stat-label {
  color: #a6adc8;
  font-size: 0.9rem;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    padding: 0 16px;
  }

  .page-title {
    font-size: 2rem;
  }

  .about-section {
    padding: 20px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .stat-card {
    justify-content: center;
    text-align: center;
  }

  .contact-links {
    flex-direction: column;
    align-items: center;
  }
}

@media (max-width: 480px) {
  .about-page {
    padding: 16px 0;
  }

  .page-title {
    font-size: 1.5rem;
  }

  .page-subtitle {
    font-size: 1rem;
  }

  .section-title {
    font-size: 1.4rem;
  }

  .about-section {
    padding: 16px;
    margin-bottom: 20px;
  }
}
</style>
