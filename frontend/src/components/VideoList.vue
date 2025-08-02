<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { API_URLS, getApiUrl, API_CONFIG } from '@/config/api.js';
import '@/assets/styles/Sort.css';
import '@/assets/styles/BackToTop.css';

const route = useRoute();
const videos = ref([]);
const originalVideos = ref([]); // 保存原始数据
const author = ref(null);
const showBackToTop = ref(false);
const avatarLoaded = ref(false); // 头像加载状态

// 从 localStorage 读取排序设置，如果没有则使用默认值
const getSavedSortSettings = () => {
  try {
    const saved = localStorage.getItem('videoList-sortSettings');
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        sortOrder: parsed.sortOrder || 'asc'
      };
    }
  } catch (error) {
    console.warn('Failed to parse saved sort settings:', error);
  }
  return { sortOrder: 'asc' }; // 默认升序，从最早的视频开始
};

const savedSettings = getSavedSortSettings();
const sortOrder = ref(savedSettings.sortOrder); // 排序顺序：asc, desc

// 保存排序设置到 localStorage
const saveSortSettings = () => {
  try {
    const settings = {
      sortOrder: sortOrder.value
    };
    localStorage.setItem('videoList-sortSettings', JSON.stringify(settings));
  } catch (error) {
    console.warn('Failed to save sort settings:', error);
  }
};

// 排序相关函数
const setSortOrder = () => {
  // 切换排序顺序
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
  
  // 保存排序设置
  saveSortSettings();
  
  sortVideos();
};

const sortVideos = () => {
  const sorted = [...originalVideos.value].sort((a, b) => {
    const dateA = a.date ? new Date(a.date) : new Date(0);
    const dateB = b.date ? new Date(b.date) : new Date(0);
    const comparison = dateA - dateB;
    
    return sortOrder.value === 'asc' ? comparison : -comparison;
  });
  
  videos.value = sorted;
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  } catch {
    return dateStr;
  }
};

const getTranslationStatusText = (status) => {
  switch (status) {
    case 1: return '中文内嵌';
    case 2: return 'CC字幕';
    case 3: return '弹幕翻译';
    case 4: return '无需翻译';
    case 5: return '暂无翻译';
    default: return '';
  }
};

const getTranslationStatusClass = (status) => {
  switch (status) {
    case 0: return 'status-none';
    case 1: return 'status-full';
    case 2: return 'status-partial';
    default: return 'status-unknown';
  }
};

const openUrl = (url) => {
  if (url) {
    // 确保 URL 有协议前缀
    const fullUrl = url.startsWith('http') ? url : `https://${url}`;
    window.open(fullUrl, '_blank', 'noopener,noreferrer');
  }
};

// 返回顶部功能
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

// 头像加载处理函数
const handleAvatarLoad = () => {
  avatarLoaded.value = true;
};

const handleAvatarError = () => {
  avatarLoaded.value = false;
};

// 监听滚动事件，控制返回顶部按钮显示
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300;
};

onMounted(async () => {
  // 添加滚动事件监听器
  window.addEventListener('scroll', handleScroll);
  
  const authorId = route.query.id;
  try {
    // 获取作者信息
    const authorRes = await fetch(API_URLS.AUTHORS);
    if (authorRes.ok) {
      const authors = await authorRes.json();
      author.value = authors.find(a => a.id == authorId);
      // 如果作者有头像，尝试预加载
      if (author.value && author.value.avatar) {
        const img = new Image();
        img.onload = () => {
          avatarLoaded.value = true;
        };
        img.onerror = () => {
          avatarLoaded.value = false;
        };
        img.src = author.value.avatar;
      }
    }
    
    // 获取视频列表
    const res = await fetch(
      getApiUrl(`/api/author/${authorId}/videos`),
    );
    if (!res.ok) throw new Error("请求失败");
    const videoData = await res.json();
    originalVideos.value = videoData;
    
    // 初始排序
    sortVideos();
  } catch (e) {
    videos.value = [];
    originalVideos.value = [];
    console.error(e);
  }
});

onUnmounted(() => {
  // 清理事件监听器
  window.removeEventListener('scroll', handleScroll);
});
</script>

<template>
  <div class="video-list-container">
    <!-- 作者信息标题 -->
    <div class="author-header" v-if="author">
      <div class="author-avatar" v-if="avatarLoaded && author.avatar">
        <img 
          :src="author.avatar" 
          :alt="author.name" 
          @load="handleAvatarLoad"
          @error="handleAvatarError"
        />
      </div>
      <div class="author-info">
        <h1 class="author-name">{{ author.name }}</h1>
        <div class="video-count">📊 {{ videos.length }} 个视频</div>
      </div>
    </div>
    
    <!-- 排序控件 -->
    <div class="sort-controls">
      <div class="sort-buttons">
        <v-btn
          class="sort-btn active"
          @click="setSortOrder()"
          size="small"
          rounded="lg"
        >
          <v-icon size="16">mdi-clock-outline</v-icon>
          <span>最近更新</span>
          <v-icon size="14">
            {{ sortOrder === 'asc' ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
          </v-icon>
        </v-btn>
      </div>
    </div>
    
    <!-- 视频列表 -->
    <div class="videos-grid">
      <div v-for="video in videos" :key="video.id" class="video-row">
        <div class="video-date" v-if="video.date">
          📅 {{ formatDate(video.date) }}
        </div>
        
        <div class="video-columns">
          <!-- 原视频列 -->
          <div 
            class="video-column original-column"
            :class="{ 'clickable-column': video.original_url, 'disabled-column': !video.original_url }"
            @click="video.original_url && openUrl(video.original_url)"
          >
            <h3 class="video-title">
               {{ video.original_name || '暂无原视频' }}
            </h3>
          </div>
          
          <!-- 转载列 -->
          <div 
            class="video-column repost-column"
            :class="{ 'clickable-column': video.repost_url, 'disabled-column': !video.repost_url }"
            @click="video.repost_url && openUrl(video.repost_url)"
          >
            <div class="repost-header">
              <h3 class="video-title">
                 {{ video.repost_name || '暂无转载' }}
              </h3>
              
              <!-- 翻译状态 -->
              <div class="translation-status" v-if="video.translation_status !== null && video.translation_status !== '' && getTranslationStatusText(video.translation_status)">
                <span :class="getTranslationStatusClass(video.translation_status)">
                  {{ getTranslationStatusText(video.translation_status) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="videos.length === 0" class="empty-text">暂无视频</div>
    </div>

    <!-- 返回顶部按钮 -->
    <v-btn
      v-if="showBackToTop"
      icon
      size="large"
      class="back-to-top-btn"
      @click="scrollToTop"
      style="position: fixed; bottom: 24px; right: 24px; z-index: 1000;"
    >
      <v-icon>mdi-chevron-up</v-icon>
    </v-btn>
  </div>
</template>

<style scoped>
.video-list-container {
  max-width: 1200px;
  margin: 20px auto;
  background: #1e1e2e; /* Catppuccin Mocha Base */
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 0;
  overflow: hidden;
}

/* 作者信息标题 */
.author-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 32px;
  background: linear-gradient(135deg, #313244 0%, #45475a 100%);
  border-bottom: 2px solid #585b70;
}

.author-avatar {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.author-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-info {
  flex: 1;
}

.author-name {
  font-size: 2rem;
  font-weight: bold;
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  margin: 0 0 8px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.video-count {
  font-size: 1.1rem;
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  background: rgba(203, 166, 247, 0.1);
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
  border: 1px solid rgba(203, 166, 247, 0.3);
}

/* 视频列表 */
.videos-grid {
  padding: 24px;
}

.video-row {
  background: #313244; /* Catppuccin Mocha Surface0 */
  border-radius: 12px;
  margin-bottom: 16px;
  padding: 20px;
  border: 1px solid #45475a;
  transition: all 0.3s ease;
}

/* 移除整行的悬停效果，改为单独列的悬停效果 */

.video-date {
  font-size: 0.9rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  background: #585b70; /* Catppuccin Mocha Surface2 */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
  margin-bottom: 16px;
}

.video-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.video-column {
  background: #45475a; /* Catppuccin Mocha Surface1 */
  border-radius: 10px;
  padding: 16px;
  border: 1px solid #585b70;
  transition: all 0.3s ease;
}

/* 可点击列的样式 */
.clickable-column {
  cursor: pointer;
}

.clickable-column:hover {
  background: #585b70; /* Catppuccin Mocha Surface2 */
  box-shadow: 0 4px 16px rgba(203, 166, 247, 0.3);
  transform: translateY(-3px);
  border-color: #6c7086;
}

.clickable-column:hover .video-title {
  color: #74c7ec; /* Catppuccin Mocha Sapphire */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* 不可点击列的样式 */
.disabled-column {
  opacity: 0.7;
  cursor: not-allowed;
}

.disabled-column .video-title {
  color: #6c7086; /* Catppuccin Mocha Overlay0 */
  font-style: italic;
}

.original-column {
  border-left: 4px solid #89b4fa; /* Catppuccin Mocha Blue */
}

.repost-column {
  border-left: 4px solid #a6e3a1; /* Catppuccin Mocha Green */
}

.video-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: #cdd6f4; /* Catppuccin Mocha Text */
  line-height: 1.4;
  transition: all 0.2s ease;
}

/* 可点击列中的标题颜色 */
.clickable-column .video-title {
  color: #89b4fa; /* Catppuccin Mocha Blue */
}

.repost-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.translation-status {
  align-self: flex-start;
}

.status-none {
  color: #f38ba8; /* Catppuccin Mocha Red */
  background: rgba(243, 139, 168, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(243, 139, 168, 0.3);
}

.status-full {
  color: #a6e3a1; /* Catppuccin Mocha Green */
  background: rgba(166, 227, 161, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(166, 227, 161, 0.3);
}

.status-partial {
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  background: rgba(249, 226, 175, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(249, 226, 175, 0.3);
}

.status-unknown {
  color: #6c7086; /* Catppuccin Mocha Overlay0 */
  background: rgba(108, 112, 134, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(108, 112, 134, 0.3);
}

.empty-text {
  text-align: center;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  font-size: 1.2rem;
  margin: 60px 0;
  font-style: italic;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .video-list-container {
    max-width: 95%;
    margin: 16px auto;
  }
  
  .author-header {
    padding: 24px 20px;
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .author-avatar {
    width: 120px;
    height: 120px;
  }
  
  .author-name {
    font-size: 1.6rem;
  }
  
  .videos-grid {
    padding: 16px;
  }
  
  .video-row {
    padding: 16px;
  }
  
  .video-columns {
    grid-template-columns: 1fr 1fr; /* 保持两列布局 */
    gap: 12px; /* 减少间距以适应小屏幕 */
  }
  
  .video-column {
    padding: 12px; /* 减少内边距 */
  }
  
  .video-title {
    font-size: 0.95rem; /* 稍微减小字体 */
  }
  
  .repost-header {
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .author-header {
    padding: 20px 16px;
  }
  
  .author-avatar {
    width: 100px;
    height: 100px;
  }
  
  .author-name {
    font-size: 1.4rem;
  }
  
  .video-count {
    font-size: 1rem;
    padding: 4px 8px;
  }
  
  .videos-grid {
    padding: 12px;
  }
  
  .video-row {
    padding: 12px;
  }
  
  .video-columns {
    grid-template-columns: 1fr 1fr; /* 超小屏幕也保持两列 */
    gap: 8px; /* 进一步减少间距 */
  }
  
  .video-column {
    padding: 8px; /* 更小的内边距 */
  }
  
  .video-title {
    font-size: 0.85rem; /* 更小的字体以适应空间 */
    line-height: 1.3;
  }
  
  .status-none,
  .status-full,
  .status-partial,
  .status-unknown {
    font-size: 0.7rem; /* 状态标签字体也相应缩小 */
    padding: 2px 6px;
  }
}
</style>
