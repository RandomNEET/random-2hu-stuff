<template>
  <div class="announcement-page">
    <div class="container">
      <!-- 页面标题 -->
      <div class="page-header">
        <v-icon size="48" class="header-icon">mdi-bullhorn</v-icon>
        <h1 class="page-title">公告</h1>
      </div>

      <!-- 最新更新 -->
      <div class="announcement-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-update</v-icon>
          <h2 class="section-title">最新更新</h2>
        </div>

        <div class="update-timeline">
          <div class="update-item">
            <div class="update-date">2025.08.03</div>
            <div class="update-content">
              <h3>日常更新</h3>
              <ul>
                <li>功能：视频列表支持按照翻译状态排序，为部分视频添加备注</li>
                <li>内容：新增20位作者，363个视频，感谢群友的整理</li>
              </ul>
            </div>
          </div>
          
          <div class="update-item">
            <div class="update-date">2025.08.01</div>
            <div class="update-content">
              <h3>🎉 网站正式部署</h3>
              <ul>
                <li>random 2hu stuff 豪华重置版成功部署，可喜可贺</li>
                <li>支持作者浏览、视频查看、搜索功能</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 共同维护 -->
      <div class="announcement-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-account-group</v-icon>
          <h2 class="section-title">共同维护</h2>
        </div>

        <div class="collaboration-simple">
          <p class="collaboration-text">
            欢迎对MMD比较熟悉的车万人一起维护网站，会编辑在线表格就行
          </p>

          <div class="group-link">
            <v-btn
              variant="outlined"
              color="blue"
              prepend-icon="mdi-account-group"
              href="https://qm.qq.com/q/NuSbWCMd8"
              target="_blank"
              class="contact-btn"
              size="large"
            >
              QQ群：976462503
            </v-btn>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";

const showBackToTop = ref(false);

// 监听滚动事件，控制返回顶部按钮显示
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300;
};

// 返回顶部功能
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

onMounted(() => {
  window.addEventListener("scroll", handleScroll);
});

onUnmounted(() => {
  window.removeEventListener("scroll", handleScroll);
});
</script>

<style scoped>
.announcement-page {
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

/* 公告区块 */
.announcement-section {
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

/* 更新时间线 */
.update-timeline {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.update-item {
  display: flex;
  gap: 24px;
  padding: 20px;
  background: rgba(30, 30, 46, 0.6);
  border-radius: 12px;
  border-left: 4px solid #89b4fa;
  transition: all 0.3s ease;
}

.update-item:hover {
  background: rgba(30, 30, 46, 0.8);
  transform: translateX(4px);
}

.update-date {
  color: #89b4fa;
  font-weight: bold;
  font-size: 0.9rem;
  min-width: 80px;
  padding-top: 4px;
}

.update-content h3 {
  color: #f9e2af;
  margin-bottom: 8px;
  font-size: 1.1rem;
}

.update-content ul {
  margin: 0;
  padding-left: 20px;
  color: #cdd6f4;
}

.update-content li {
  margin-bottom: 4px;
  line-height: 1.5;
}

/* 合作区块 */
.collaboration-simple {
  text-align: center;
  padding: 20px 0;
}

.collaboration-text {
  color: #a6adc8;
  font-size: 1.1rem;
  line-height: 1.8;
  margin-bottom: 32px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.group-link {
  margin-top: 24px;
}

.contact-btn {
  color: #89b4fa !important;
  border-color: #89b4fa !important;
  padding: 12px 32px;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.contact-btn:hover {
  background-color: rgba(137, 180, 250, 0.1) !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    padding: 0 16px;
  }

  .page-title {
    font-size: 2rem;
  }

  .announcement-section {
    padding: 20px;
  }

  .update-item {
    flex-direction: column;
    gap: 12px;
  }

  .update-date {
    min-width: auto;
  }

  .collaboration-text {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .announcement-page {
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

  .announcement-section {
    padding: 16px;
    margin-bottom: 20px;
  }

  .collaboration-text {
    font-size: 0.95rem;
  }
}
</style>
