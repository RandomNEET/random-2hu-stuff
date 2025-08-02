<template>
  <v-app-bar
    app
    elevation="4"
    class="app-header"
    height="70"
  >
    <v-container class="d-flex align-center">
      <!-- 网站标题 -->
      <div class="site-title" @click="$router.push('/')" style="cursor: pointer">
        <h1 class="title-text">random 2hu stuff</h1>
      </div>

      <v-spacer></v-spacer>

      <!-- 搜索栏 -->
      <div class="search-container">
        <v-text-field
          v-model="searchQuery"
          placeholder="搜索作者或视频..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          hide-details
          class="search-field desktop-search"
          @keyup.enter="handleSearch"
        />
      </div>

      <v-spacer></v-spacer>

      <!-- 导航菜单 -->
      <div class="nav-menu">
        <!-- 手机端搜索按钮 -->
        <v-btn
          icon
          class="mobile-search-btn"
          @click="showMobileSearch = !showMobileSearch"
        >
          <v-icon>mdi-magnify</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/')"
        >
          <v-icon>mdi-home</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/announcement')"
        >
          <v-icon>mdi-bullhorn</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/about')"
        >
          <v-icon>mdi-information</v-icon>
        </v-btn>
      </div>
    </v-container>

    <!-- 手机端弹出搜索框 -->
    <div v-if="showMobileSearch" class="mobile-search-overlay" @click="showMobileSearch = false">
      <div class="mobile-search-popup" @click.stop>
        <v-text-field
          v-model="searchQuery"
          placeholder="搜索作者或视频..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          hide-details
          class="search-field mobile-popup-search"
          @keyup.enter="handleMobileSearch"
          autofocus
        />
        <v-btn
          icon
          class="close-btn"
          @click="showMobileSearch = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </div>
    </div>
  </v-app-bar>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const searchQuery = ref('');
const showMobileSearch = ref(false);

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    // 跳转到搜索结果页面，并传递搜索参数
    router.push({
      path: '/search',
      query: { q: searchQuery.value.trim() }
    });
  }
};

const handleMobileSearch = () => {
  if (searchQuery.value.trim()) {
    // 跳转到搜索结果页面，并传递搜索参数
    router.push({
      path: '/search',
      query: { q: searchQuery.value.trim() }
    });
    showMobileSearch.value = false; // 关闭弹出层
  }
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.app-header {
  background: linear-gradient(135deg, #1e1e2e 0%, #313244 100%) !important; /* Catppuccin Mocha gradient */
  border-bottom: 2px solid #45475a; /* Catppuccin Mocha Surface1 */
  font-family: 'JetBrains Mono', 'JetBrainsMono Nerd Font', monospace !important;
}

.app-header * {
  font-family: 'JetBrains Mono', 'JetBrainsMono Nerd Font', monospace !important;
}

.site-title {
  transition: transform 0.2s ease;
  flex-shrink: 0; /* 防止标题被压缩 */
}

.site-title:hover {
  transform: scale(1.05);
}

.title-text {
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.search-container {
  max-width: 400px;
  width: 100%;
}

.mobile-search-container {
  display: none; /* 默认隐藏手机端搜索 */
  width: 100px;
  margin-right: 8px;
}

.mobile-search-btn {
  display: none; /* 默认隐藏手机端搜索按钮 */
  color: #cdd6f4 !important;
  transition: all 0.2s ease;
}

.mobile-search-btn:hover {
  background-color: rgba(137, 180, 250, 0.1) !important;
  color: #89b4fa !important;
}

.desktop-search {
  display: block; /* 默认显示桌面端搜索 */
}

.mobile-search {
  display: none; /* 默认隐藏手机端搜索 */
}

.search-field :deep(.v-field) {
  background-color: #45475a !important; /* Catppuccin Mocha Surface1 */
  border-radius: 12px;
}

.search-field :deep(.v-field__input) {
  color: #cdd6f4 !important; /* Catppuccin Mocha Text */
}

.search-field :deep(.v-field__outline) {
  border-color: #585b70 !important; /* Catppuccin Mocha Surface2 */
}

.search-field :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important; /* Catppuccin Mocha Blue */
}

.search-field :deep(.v-field__prepend-inner .v-icon) {
  color: #a6adc8 !important; /* Catppuccin Mocha Subtext0 */
}

.search-field :deep(::placeholder) {
  color: #6c7086 !important; /* Catppuccin Mocha Overlay0 */
}

.nav-menu {
  display: flex;
  gap: 8px;
  flex-shrink: 0; /* 防止在小屏幕上被压缩 */
  align-items: center; /* 确保按钮垂直居中对齐 */
}

.nav-button {
  color: #cdd6f4 !important; /* Catppuccin Mocha Text */
  transition: all 0.2s ease;
}

.nav-button:hover {
  background-color: rgba(137, 180, 250, 0.1) !important; /* Catppuccin Mocha Blue with opacity */
  color: #89b4fa !important; /* Catppuccin Mocha Blue */
}

/* 手机端弹出搜索框样式 */
.mobile-search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 2000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px; /* 留出header空间 */
}

.mobile-search-popup {
  background: #1e1e2e;
  border-radius: 16px;
  padding: 20px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border: 1px solid #45475a;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-popup-search {
  flex: 1;
}

.close-btn {
  color: #cdd6f4 !important;
  flex-shrink: 0;
}

.close-btn:hover {
  background-color: rgba(243, 139, 168, 0.1) !important;
  color: #f38ba8 !important;
}

/* 响应式设计 */
@media (max-width: 960px) {
  .title-text {
    font-size: 1.2rem;
  }
  
  .search-container {
    display: none; /* 隐藏桌面端搜索框 */
  }
  
  .desktop-search {
    display: none !important; /* 隐藏桌面端搜索 */
  }
  
  .mobile-search-btn {
    display: flex !important; /* 显示手机端搜索按钮 */
  }
}

@media (max-width: 600px) {
  .app-header :deep(.v-container) {
    padding: 0 12px !important; /* 手机端适当padding */
  }
  
  .title-text {
    font-size: 1rem;
  }
  
  .nav-menu {
    gap: 4px; /* 减少按钮间距 */
  }
  
  .nav-button {
    min-width: 40px !important; /* 图标按钮最小宽度 */
    padding: 0 8px !important;
  }
  
  .mobile-search-btn {
    min-width: 40px !important;
    padding: 0 8px !important;
  }
  
  .mobile-search-popup {
    width: 95%;
    padding: 16px;
  }
}
</style>
