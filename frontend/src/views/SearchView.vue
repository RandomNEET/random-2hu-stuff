<template>
  <div class="search-container">
    <div class="search-content">
      <h1 class="search-title">搜索结果</h1>

      <div class="search-info" v-if="searchQuery">
        <p class="search-query">
          搜索关键词：<span class="query-text">"{{ searchQuery }}"</span>
        </p>
        <p class="search-stats">
          找到 {{ filteredAuthors.length }} 个作者，{{ searchedVideos.length }}
          个视频
        </p>
      </div>

      <!-- Video search results section with detailed video information -->
      <div v-if="searchedVideos.length > 0" class="results-section">
        <h2 class="section-title">相关视频</h2>
        <div class="videos-list">
          <div
            v-for="video in searchedVideos"
            :key="video.id"
            class="video-row"
          >
            <div class="video-header-row">
              <div class="video-info-section">
                <div class="left-info">
                  <div class="video-date" v-if="video.date">
                    📅 {{ formatDate(video.date) }}
                  </div>

                  <div class="video-comment" v-if="video.comment">
                    {{ video.comment }}
                  </div>
                </div>

                <div
                  class="author-info-small"
                  @click="goToAuthor(video.author_id, video.author_name)"
                >
                  <v-avatar size="24" class="author-avatar-small">
                    <v-img :src="video.author_avatar" />
                  </v-avatar>
                  <span class="author-name-small">{{ video.author_name }}</span>
                </div>
              </div>
            </div>

            <div class="video-columns">
              <!-- Original video column with thumbnail and metadata -->
              <div
                class="video-column original-column"
                :class="{
                  'clickable-column': video.original_url,
                  'disabled-column': !video.original_url,
                }"
                @click="video.original_url && openUrl(video.original_url)"
              >
                <!-- Original video thumbnail with loading states -->
                <div
                  v-if="video.original_thumbnail"
                  class="thumbnail-container"
                >
                  <div
                    v-if="isThumbnailLoading(video.id, 'original')"
                    class="thumbnail-loading"
                  >
                    <v-progress-circular
                      size="20"
                      width="2"
                      color="primary"
                      indeterminate
                    ></v-progress-circular>
                    <span class="loading-text">封面加载中</span>
                  </div>
                  <img
                    v-show="
                      !isThumbnailLoading(video.id, 'original') &&
                      !hasThumbnailError(video.id, 'original')
                    "
                    :src="video.original_thumbnail"
                    alt="原版封面"
                    class="video-thumbnail"
                    :class="{
                      loaded: !isThumbnailLoading(video.id, 'original'),
                    }"
                    @load="handleThumbnailLoad(video.id, 'original')"
                    @error="handleThumbnailError(video.id, 'original')"
                    @loadstart="initThumbnailLoading(video.id, 'original')"
                  />
                  <div
                    v-if="hasThumbnailError(video.id, 'original')"
                    class="thumbnail-error"
                  >
                    封面加载失败
                  </div>
                </div>

                <div class="original-header">
                  <h3 class="video-title">
                    {{ video.original_name || "暂无原视频" }}
                  </h3>

                  <!-- Video source platform indicator -->
                  <div
                    class="video-source"
                    v-if="
                      video.original_url && getVideoSource(video.original_url)
                    "
                  >
                    <span :class="getVideoSource(video.original_url).class">
                      {{ getVideoSource(video.original_url).text }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Repost video column with translation status -->
                            <!-- Repost video column with translation status -->
              <div
                class="video-column repost-column"
                :class="{
                  'clickable-column': video.repost_url,
                  'disabled-column': !video.repost_url,
                }"
                @click="video.repost_url && openUrl(video.repost_url)"
              >
                <!-- Repost video thumbnail with CORS handling -->
                <div v-if="video.repost_thumbnail" class="thumbnail-container">
                  <div
                    v-if="isThumbnailLoading(video.id, 'repost')"
                    class="thumbnail-loading"
                  >
                    <v-progress-circular
                      size="20"
                      width="2"
                      color="primary"
                      indeterminate
                    ></v-progress-circular>
                    <span class="loading-text">封面加载中</span>
                  </div>
                  <img
                    v-show="
                      !isThumbnailLoading(video.id, 'repost') &&
                      !hasThumbnailError(video.id, 'repost')
                    "
                    :src="video.repost_thumbnail"
                    alt="转载封面"
                    class="video-thumbnail"
                    :class="{ loaded: !isThumbnailLoading(video.id, 'repost') }"
                    referrerpolicy="no-referrer"
                    crossorigin="anonymous"
                    @load="handleThumbnailLoad(video.id, 'repost')"
                    @error="handleThumbnailError(video.id, 'repost')"
                    @loadstart="initThumbnailLoading(video.id, 'repost')"
                  />
                  <div
                    v-if="hasThumbnailError(video.id, 'repost')"
                    class="thumbnail-error"
                  >
                    封面加载失败
                  </div>
                </div>

                <div class="repost-header">
                  <h3 class="video-title">
                    {{ video.repost_name || "暂无转载" }}
                  </h3>

                  <!-- Translation status indicator with color coding -->
                  <div
                    class="translation-status"
                    v-if="
                      video.translation_status !== null &&
                      video.translation_status !== '' &&
                      getTranslationStatusText(video.translation_status)
                    "
                  >
                    <span
                      :class="
                        getTranslationStatusClass(video.translation_status)
                      "
                    >
                      {{ getTranslationStatusText(video.translation_status) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Author search results with grid layout -->
      <div v-if="filteredAuthors.length > 0" class="results-section">
        <h2 class="section-title">相关作者</h2>
        <div class="authors-grid">
          <v-card
            v-for="author in filteredAuthors"
            :key="author.id"
            class="author-card"
            elevation="3"
            hover
            @click="
              $router.push({
                path: `/author/${author.name}`,
                query: { id: author.id },
              })
            "
          >
            <v-img :src="author.avatar" class="author-avatar" />
            <div class="author-info">
              <div class="author-name">{{ author.name }}</div>
              <div class="author-works">视频数：{{ author.worksCount }}</div>
            </div>
          </v-card>
        </div>
      </div>

      <!-- No results found message with helpful suggestions -->
            <!-- No results found message with helpful suggestions -->
      <div
        v-if="
          searchQuery &&
          filteredAuthors.length === 0 &&
          searchedVideos.length === 0
        "
        class="no-results"
      >
        <v-icon size="64" color="#6c7086">mdi-magnify-remove-outline</v-icon>
        <h3>未找到相关结果</h3>
        <p>尝试使用不同的关键词进行搜索</p>
        <v-btn color="primary" @click="$router.push('/')" class="back-home-btn">
          返回首页
        </v-btn>
      </div>

      <!-- Search tips and suggestions for users -->
      <div v-if="!searchQuery" class="search-tips">
        <h3 class="tips-title">搜索提示</h3>
        <ul class="tips-list">
          <li>支持模糊搜索，输入部分名称即可</li>
        </ul>
      </div>
    </div>

    <!-- Back to top button with smooth scrolling -->
    <v-btn
      v-if="showBackToTop"
      icon
      size="large"
      class="back-to-top-btn"
      @click="scrollToTop"
      style="position: fixed; bottom: 24px; right: 24px; z-index: 1000"
    >
      <v-icon>mdi-chevron-up</v-icon>
    </v-btn>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { API_URLS, getApiUrl, API_CONFIG } from "@/config/api.js";
import "@/assets/styles/BackToTop.css";

const route = useRoute();
const router = useRouter();
const authors = ref([]);
const searchedVideos = ref([]);
const searchQuery = ref("");
const showBackToTop = ref(false);

// Thumbnail loading state management for video thumbnails
// Maps video IDs with type (original/repost) to loading states
const thumbnailLoadingStates = ref(new Map());
const thumbnailErrorStates = ref(new Map());

// Handle successful thumbnail load - remove loading state
const handleThumbnailLoad = (videoId, type) => {
  const key = `${videoId}_${type}`;
  thumbnailLoadingStates.value.set(key, false);
};

// Handle thumbnail load error - set error state and stop loading
const handleThumbnailError = (videoId, type) => {
  const key = `${videoId}_${type}`;
  thumbnailLoadingStates.value.set(key, false);
  thumbnailErrorStates.value.set(key, true);
};

// Initialize thumbnail loading state when load starts
const initThumbnailLoading = (videoId, type) => {
  const key = `${videoId}_${type}`;
  thumbnailLoadingStates.value.set(key, true);
  thumbnailErrorStates.value.set(key, false);
};

// Check if thumbnail is currently loading
const isThumbnailLoading = (videoId, type) => {
  const key = `${videoId}_${type}`;
  return thumbnailLoadingStates.value.get(key) || false;
};

// Check if thumbnail has failed to load
const hasThumbnailError = (videoId, type) => {
  const key = `${videoId}_${type}`;
  return thumbnailErrorStates.value.get(key) || false;
};

// Format date string to Chinese locale format
// Format date string to Chinese locale format
const formatDate = (dateStr) => {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return dateStr;
  }
};

// Get translation status text based on numeric status code
const getTranslationStatusText = (status) => {
  switch (status) {
    case 1:
      return "中文内嵌";
    case 2:
      return "CC字幕";
    case 3:
      return "弹幕翻译";
    case 4:
      return "无需翻译";
    case 5:
      return "暂无翻译";
    default:
      return "";
  }
};

// Detect video platform from URL and return display info
// Detect video platform from URL and return display info
const getVideoSource = (url) => {
  if (!url) return null;

  const lowerUrl = url.toLowerCase();

  if (lowerUrl.includes("youtube.com") || lowerUrl.includes("youtu.be")) {
    return { text: "YouTube", class: "source-youtube" };
  } else if (
    lowerUrl.includes("nicovideo.jp") ||
    lowerUrl.includes("nico.ms")
  ) {
    return { text: "NicoNico", class: "source-niconico" };
  } else if (lowerUrl.includes("bilibili.com")) {
    return { text: "Bilibili", class: "source-bilibili" };
  } else if (lowerUrl.includes("twitter.com") || lowerUrl.includes("x.com")) {
    return { text: "Twitter/X", class: "source-twitter" };
  } else {
    return { text: "其他", class: "source-other" };
  }
};

// Get CSS class for translation status styling
const getTranslationStatusClass = (status) => {
  switch (status) {
    case 0:
      return "status-none";
    case 1:
      return "status-full";
    case 2:
      return "status-partial";
    case 3:
      return "status-partial";
    default:
      return "status-unknown";
  }
};

// Navigate to author detail page with proper routing
const goToAuthor = (authorId, authorName) => {
  router.push({
    path: `/author/${authorName}`,
    query: { id: authorId },
  });
};

// Open external URL in new tab with security measures
const openUrl = (url) => {
  if (url) {
    // Ensure URL has protocol prefix for security
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};

// Filter authors based on search query with fuzzy matching
// Filter authors based on search query with fuzzy matching
const filteredAuthors = computed(() => {
  if (!searchQuery.value) return [];

  const query = searchQuery.value.toLowerCase();
  return authors.value
    .filter(
      (author) =>
        author.name.toLowerCase().includes(query) ||
        (author.url && author.url.toLowerCase().includes(query)),
    )
    .sort((a, b) => b.worksCount - a.worksCount); // Sort by video count descending
});

// Calculate total videos from filtered authors (currently unused)
const totalVideos = computed(() => {
  return filteredAuthors.value.reduce(
    (sum, author) => sum + author.worksCount,
    0,
  );
});

// Fetch all authors data from API
const fetchAuthors = async () => {
  try {
    const res = await fetch(API_URLS.AUTHORS);
    authors.value = await res.json();
  } catch (error) {
    console.error("获取作者数据失败:", error);
  }
};

// Search videos by query string using API endpoint
const searchVideos = async (query) => {
  if (!query) {
    searchedVideos.value = [];
    return;
  }

  try {
    const res = await fetch(
      `${API_URLS.SEARCH_VIDEOS}?q=${encodeURIComponent(query)}`,
    );
    if (res.ok) {
      searchedVideos.value = await res.json();
    } else {
      searchedVideos.value = [];
    }
  } catch (error) {
    console.error("搜索视频失败:", error);
    searchedVideos.value = [];
  }
};

// Perform search operation (wrapper function for future enhancements)
const performSearch = (query) => {
  searchVideos(query);
};

// Smooth scroll to top of page
const scrollToTop = () => {
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
};

// Handle scroll events to show/hide back-to-top button
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300;
};

// Component lifecycle: setup and cleanup
onMounted(() => {
  fetchAuthors(); // Load authors data on component mount
  const initialQuery = route.query.q || "";
  searchQuery.value = initialQuery;
  if (initialQuery) {
    performSearch(initialQuery);
  }

  // Add scroll listener for back-to-top button
  window.addEventListener("scroll", handleScroll);
});

onUnmounted(() => {
  // Remove scroll listener to prevent memory leaks
  window.removeEventListener("scroll", handleScroll);
});

// Watch for route query changes to update search
watch(
  () => route.query.q,
  (newQuery) => {
    const query = newQuery || "";
    searchQuery.value = query;
    performSearch(query);
  },
);
</script>

<style scoped>
/* Main search container with Catppuccin Mocha color scheme */
.search-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px;
  background: #1e1e2e; /* Catppuccin Mocha Base */
  min-height: calc(100vh - 70px); /* Full height minus header */
}

/* Search content card with glassmorphism effect */
.search-content {
  background: #313244; /* Catppuccin Mocha Surface0 */
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); /* Deep shadow for depth */
  border: 1px solid #45475a; /* Catppuccin Mocha Surface1 */
}

/* Main search results title */
.search-title {
  text-align: center;
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 32px;
}

/* Search information display card */
.search-info {
  text-align: center;
  margin-bottom: 32px;
  padding: 16px;
  background: #45475a; /* Catppuccin Mocha Surface1 */
  border-radius: 12px;
}

/* Search query display text */
.search-query {
  color: #cdd6f4; /* Catppuccin Mocha Text */
  font-size: 1.2rem;
  margin: 0 0 8px 0;
}

/* Highlighted query text */
.query-text {
  color: #89b4fa; /* Catppuccin Mocha Blue */
  font-weight: bold;
}

/* Search statistics text */
.search-stats {
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  font-size: 1rem;
  margin: 0;
}

/* Section containers for results */
.results-section {
  margin-bottom: 32px;
}

/* Section titles with underline */
.section-title {
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 20px;
  border-bottom: 2px solid #45475a;
  padding-bottom: 8px;
}

/* Responsive grid layout for author cards */
.authors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

/* Video list with vertical stacking */
.videos-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

/* Video list with vertical stacking */
.videos-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

/* Individual video row container with hover effects */
.video-row {
  background: #313244; /* Catppuccin Mocha Surface0 */
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #45475a;
  transition: all 0.3s ease; /* Smooth hover transitions */
}

/* Video header row with metadata and author info */
.video-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}

/* Video information section layout */
.video-info-section {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}

/* Left side information grouping */
.left-info {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

/* Video date display with background */
.video-date {
  font-size: 0.9rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  background: #585b70; /* Catppuccin Mocha Surface2 */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
}

/* Video comment/note display with special styling */
.video-comment {
  font-size: 0.9rem;
  color: #f2cdcd; /* Catppuccin Mocha Flamingo */
  background: rgba(242, 205, 205, 0.15); /* Semi-transparent flamingo */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
  border: 1px solid rgba(242, 205, 205, 0.3);
  font-style: italic; /* Italicized for comment appearance */
}

/* Small author info component with click interaction */

/* Small author info component with click interaction */
.author-info-small {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease; /* Smooth hover effect */
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(137, 180, 250, 0.1); /* Subtle blue background */
}

/* Author info hover effect with scaling */
.author-info-small:hover {
  background: rgba(137, 180, 250, 0.2); /* Darker blue on hover */
  transform: scale(1.05); /* Slight scale effect */
}

/* Small author name styling */
.author-name-small {
  color: #89b4fa; /* Catppuccin Mocha Blue */
  font-size: 0.9rem;
  font-weight: 600;
}

/* Small author avatar with border */
.author-avatar-small {
  border: 1px solid #585b70;
}

/* Two-column grid for video comparison */
.video-columns {
  display: grid;
  grid-template-columns: 1fr 1fr; /* Equal width columns */
  gap: 20px;
}

/* Base video column styling with transitions */
.video-column {
  background: #45475a; /* Catppuccin Mocha Surface1 */
  border-radius: 10px;
  padding: 16px;
  border: 1px solid #585b70;
  transition: all 0.3s ease; /* Smooth hover transitions */
}

/* Clickable column styling with hover effects */
.clickable-column {
  cursor: pointer;
}

.clickable-column:hover {
  background: #585b70; /* Catppuccin Mocha Surface2 on hover */
  box-shadow: 0 4px 16px rgba(203, 166, 247, 0.3); /* Mauve glow effect */
  transform: translateY(-3px); /* Lift effect */
  border-color: #6c7086;
}

/* Hover effect for clickable video titles */
.clickable-column:hover .video-title {
  color: #74c7ec; /* Catppuccin Mocha Sapphire */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* Disabled column styling for unavailable videos */
.disabled-column {
  opacity: 0.7;
  cursor: not-allowed;
}

.disabled-column .video-title {
  color: #6c7086; /* Catppuccin Mocha Overlay0 - muted */
  font-style: italic;
}

/* Original video column with blue accent */
.original-column {
  border-left: 4px solid #89b4fa; /* Catppuccin Mocha Blue */
}

/* Repost video column with green accent */
.repost-column {
  border-left: 4px solid #a6e3a1; /* Catppuccin Mocha Green */
}

/* Video title styling with transitions */

.video-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: #cdd6f4;
  /* Catppuccin Mocha Text */
  line-height: 1.4;
  transition: all 0.2s ease;
}

/* 可点击列中的标题颜色 */
.clickable-column .video-title {
  color: #89b4fa;
  /* Catppuccin Mocha Blue */
}

/* 缩略图样式 */
.thumbnail-container {
  position: relative;
  width: 100%;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  background: #585b70;
  /* Catppuccin Mocha Surface2 */
  margin-bottom: 12px;
}

.video-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition:
    transform 0.3s ease,
    opacity 0.3s ease;
  opacity: 0;
  /* 初始透明 */
}

.video-thumbnail.loaded {
  opacity: 1;
  /* 加载完成后显示 */
}

.thumbnail-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #585b70;
  z-index: 1;
  gap: 12px;
}

.loading-text {
  color: #a6adc8;
  /* Catppuccin Mocha Subtext0 */
  font-size: 0.9rem;
  text-align: center;
}

.thumbnail-error {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #585b70;
  color: #f38ba8;
  /* Catppuccin Mocha Red */
  font-size: 0.9rem;
  text-align: center;
  z-index: 1;
}

.clickable-column:hover .video-thumbnail {
  transform: scale(1.05);
}

.repost-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.original-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-source {
  align-self: flex-start;
}

.translation-status {
  align-self: flex-start;
}

.status-none {
  color: #f38ba8;
  /* Catppuccin Mocha Red */
  background: rgba(243, 139, 168, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(243, 139, 168, 0.3);
}

.status-full {
  color: #a6e3a1;
  /* Catppuccin Mocha Green */
  background: rgba(166, 227, 161, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(166, 227, 161, 0.3);
}

.status-partial {
  color: #f9e2af;
  /* Catppuccin Mocha Yellow */
  background: rgba(249, 226, 175, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(249, 226, 175, 0.3);
}

.status-unknown {
  color: #6c7086;
  /* Catppuccin Mocha Overlay0 */
  background: rgba(108, 112, 134, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(108, 112, 134, 0.3);
}

/* 视频来源样式 */
.source-youtube {
  color: #f38ba8;
  /* Catppuccin Mocha Red */
  background: rgba(243, 139, 168, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(243, 139, 168, 0.3);
}

.source-niconico {
  color: #fab387;
  /* Catppuccin Mocha Peach */
  background: rgba(250, 179, 135, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(250, 179, 135, 0.3);
}

.source-bilibili {
  color: #89b4fa;
  /* Catppuccin Mocha Blue */
  background: rgba(137, 180, 250, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(137, 180, 250, 0.3);
}

.source-twitter {
  color: #74c7ec;
  /* Catppuccin Mocha Sapphire */
  background: rgba(116, 199, 236, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(116, 199, 236, 0.3);
}

.source-other {
  color: #cba6f7;
  /* Catppuccin Mocha Mauve */
  background: rgba(203, 166, 247, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(203, 166, 247, 0.3);
}

.author-card {
  background: #45475a !important;
  /* Catppuccin Mocha Surface1 */
  border: 1px solid #585b70;
  /* Catppuccin Mocha Surface2 */
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 16px;
  overflow: hidden;
  /* 确保内容不超出圆角边界 */
  display: flex;
  flex-direction: column;
}

.author-card:hover {
  background: #585b70 !important;
  /* Catppuccin Mocha Surface2 */
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(203, 166, 247, 0.15);
}

.author-avatar {
  width: 100%;
  aspect-ratio: 1;
  /* 保持正方形比例 */
  object-fit: cover;
  flex-shrink: 0;
  /* 防止压缩 */
}

/* 强制 Vuetify v-img 组件填满容器 */
.author-avatar :deep(.v-img__img) {
  object-fit: cover !important;
  width: 100% !important;
  height: 100% !important;
}

.author-info {
  padding: 16px;
  text-align: center;
  flex: 1;
  /* 占据剩余空间 */
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.author-name {
  color: #f9e2af;
  /* Catppuccin Mocha Yellow */
  font-size: 1.1rem;
  font-weight: bold;
  margin-bottom: 8px;
}

.author-works {
  color: #cba6f7;
  /* Catppuccin Mocha Mauve */
  font-size: 0.9rem;
}

.no-results {
  text-align: center;
  padding: 60px 20px;
  color: #a6adc8;
  /* Catppuccin Mocha Subtext0 */
}

.no-results h3 {
  color: #cdd6f4;
  /* Catppuccin Mocha Text */
  margin: 16px 0 8px 0;
}

.no-results p {
  margin-bottom: 24px;
}

.back-home-btn {
  background: linear-gradient(90deg, #89b4fa, #74c7ec) !important;
  /* Catppuccin Mocha Blue to Sapphire */
  color: #1e1e2e !important;
  font-weight: 600;
}

.search-tips {
  text-align: center;
  padding: 40px 20px;
}

.tips-title {
  color: #cba6f7;
  /* Catppuccin Mocha Mauve */
  margin-bottom: 20px;
}

.tips-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-width: 400px;
  margin: 0 auto;
}

.tips-list li {
  color: #cdd6f4;
  /* Catppuccin Mocha Text */
  padding: 8px 0;
  border-bottom: 1px solid rgba(69, 71, 90, 0.3);
}

.tips-list li:last-child {
  border-bottom: none;
}

/* Responsive design breakpoints for optimal mobile experience */
/* Tablet and medium screen optimizations */
@media (max-width: 834px) {
  /* Reduced container padding for smaller screens */
  .search-container {
    padding: 20px 16px;
  }

  /* Smaller content padding on tablets */
  .search-content {
    padding: 24px 20px;
  }

  /* Smaller main title for tablet screens */
  .search-title {
    font-size: 2rem;
  }

  /* Adjusted author grid for medium screens */
  .authors-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
  }

  /* Reduced video row padding */
  .video-row {
    padding: 16px;
  }

  /* Stack video header elements vertically on tablets */
  .video-header-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  /* Maintain horizontal layout for video info */
  .video-info-section {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  /* Compact left info layout */
  .left-info {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  /* Keep two-column video layout on tablets */
  .video-columns {
    grid-template-columns: 1fr 1fr;
    gap: 12px; /* Reduced gap for smaller screens */
  }

  /* Smaller column padding on tablets */
  .video-column {
    padding: 12px;
  }

  /* Reduced thumbnail height for mobile viewing */
  .thumbnail-container {
    height: 200px;
  }

  /* Slightly smaller video titles */
  .video-title {
    font-size: 0.95rem;
  }

  /* Reduced header gaps */
  .repost-header {
    gap: 8px;
  }

  .original-header {
    gap: 8px;
  }
}

/* Mobile phone optimizations */
@media (max-width: 480px) {
  /* Minimal mobile padding */
  .video-row {
    padding: 12px;
  }

  /* Compact video info layout for small screens */
  .video-info-section {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }

  /* Tighter left info spacing */
  .left-info {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }

  /* Maintain dual column layout even on small phones */
  .video-columns {
    grid-template-columns: 1fr 1fr;
    gap: 8px; /* Minimal gap for space efficiency */
  }

  /* Minimal column padding for small screens */
  .video-column {
    padding: 8px;
  }

  /* Very small thumbnail height for phones */
  .thumbnail-container {
    height: 100px;
  }

  /* Smaller loading and error text */
  .loading-text,
  .thumbnail-error {
    font-size: 0.8rem;
  }

  /* Compact video titles for mobile */
  .video-title {
    font-size: 0.85rem;
    line-height: 1.3;
  }

  /* Smaller status and source badges */
  .status-none,
  .status-full,
  .status-partial,
  .status-unknown,
  .source-youtube,
  .source-niconico,
  .source-bilibili,
  .source-twitter,
  .source-other {
    font-size: 0.7rem;
    padding: 2px 6px;
  }

  /* Compact video comment styling */
  .video-comment {
    font-size: 0.8rem;
    padding: 4px 8px;
  }
}

/* Extra small screen optimizations (very small phones) */
@media (max-width: 360px) {
  /* Stack video info vertically on tiny screens */
  .video-info-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  /* Right-align author info on tiny screens */
  .author-info-small {
    align-self: flex-end;
  }
}
</style>
