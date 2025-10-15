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
        <div class="section-header">
          <h2 class="section-title">相关视频</h2>

          <!-- Sort controls -->
          <div class="sort-controls">
            <div class="sort-buttons">
              <v-btn
                class="sort-btn"
                :class="{ active: sortType === 'date' }"
                @click="setSortType('date')"
                size="small"
                rounded="lg"
              >
                <v-icon size="16">mdi-clock-outline</v-icon>
                <span>按时间</span>
                <v-icon size="14" v-if="sortType === 'date'">
                  {{
                    sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down"
                  }}
                </v-icon>
              </v-btn>

              <v-btn
                class="sort-btn"
                :class="{ active: sortType === 'translation' }"
                @click="setSortType('translation')"
                size="small"
                rounded="lg"
              >
                <v-icon size="16">mdi-translate</v-icon>
                <span>按翻译</span>
                <v-icon size="14" v-if="sortType === 'translation'">
                  {{
                    sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down"
                  }}
                </v-icon>
              </v-btn>

              <v-btn
                class="sort-btn"
                :class="{ active: sortType === 'relevance' }"
                @click="setSortType('relevance')"
                size="small"
                rounded="lg"
              >
                <v-icon size="16">mdi-star-outline</v-icon>
                <span>按相关性</span>
                <v-icon size="14" v-if="sortType === 'relevance'">
                  {{
                    sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down"
                  }}
                </v-icon>
              </v-btn>
            </div>
          </div>
        </div>

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
                  @click="
                    goToAuthor(video.author_id, getVideoAuthorName(video))
                  "
                >
                  <v-avatar size="24" class="author-avatar-small">
                    <v-img :src="getVideoAuthorAvatar(video)" />
                  </v-avatar>
                  <span class="author-name-small">{{
                    getVideoAuthorName(video)
                  }}</span>
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
                    :alt="video.original_name || '原视频'"
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
                    :alt="video.repost_name || '转载视频'"
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
            @click="$router.push(`/author/${author.id}`)"
          >
            <v-img :src="getDisplayAvatar(author)" class="author-avatar" />
            <div class="author-info">
              <div class="author-name">{{ getDisplayName(author) }}</div>
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
import "@/assets/styles/Sort.css";

const route = useRoute();
const router = useRouter();
const authors = ref([]);
const searchedVideos = ref([]);
const originalSearchedVideos = ref([]); // Store original search results
const searchQuery = ref("");
const showBackToTop = ref(false);

// Sort settings - load from localStorage with search-specific key
const getSavedSortSettings = () => {
  try {
    const saved = localStorage.getItem("searchView-sortSettings");
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (error) {
    console.warn("Failed to parse saved sort settings:", error);
  }
  return {
    sortType: "relevance", // Default sort by relevance
    sortOrder: "asc", // Default ascending order
  };
};

const savedSettings = getSavedSortSettings();
const sortType = ref(savedSettings.sortType); // Sort type: date, translation
const sortOrder = ref(savedSettings.sortOrder); // Sort order: asc, desc

// Save sort settings to localStorage
const saveSortSettings = () => {
  try {
    const settings = {
      sortType: sortType.value,
      sortOrder: sortOrder.value,
    };
    localStorage.setItem("searchView-sortSettings", JSON.stringify(settings));
  } catch (error) {
    console.warn("Failed to save sort settings:", error);
  }
};

// Custom video title comparison function with Chinese-Japanese-English friendly sorting
// and special numeric handling for titles with same length and containing numbers
const compareVideoTitles = (titleA, titleB) => {
  // If titles have same length and both contain numbers (1-9 or 一-九), check similarity for series detection
  if (
    titleA.length === titleB.length &&
    titleA.length > 0 &&
    titleB.length > 0
  ) {
    const getNumber = (title) => {
      // Extract Arabic numbers (1-9)
      const arabicMatch = title.match(/[1-9]/);
      if (arabicMatch) {
        return parseInt(arabicMatch[0]);
      }

      // Extract Chinese numbers (一-九)
      const chineseNumbers = {
        一: 1,
        二: 2,
        三: 3,
        四: 4,
        五: 5,
        六: 6,
        七: 7,
        八: 8,
        九: 9,
      };
      const chineseMatch = title.match(/[一二三四五六七八九]/);
      if (chineseMatch) {
        return chineseNumbers[chineseMatch[0]];
      }

      return null;
    };

    // Calculate title similarity (excluding numbers)
    const calculateSimilarity = (str1, str2) => {
      // Remove numbers and normalize titles for similarity comparison
      const normalize = (str) =>
        normalizeTextForSearch(str)
          .replace(/[1-9一二三四五六七八九]/g, "")
          .trim();
      const normalized1 = normalize(str1);
      const normalized2 = normalize(str2);

      // Simple similarity check: if normalized titles are identical or very similar
      if (normalized1 === normalized2) return 1.0;

      // Levenshtein distance for similarity calculation (works well for CJK and Latin scripts)
      const getLevenshteinDistance = (a, b) => {
        if (a.length === 0) return b.length;
        if (b.length === 0) return a.length;

        const matrix = [];
        for (let i = 0; i <= b.length; i++) {
          matrix[i] = [i];
        }
        for (let j = 0; j <= a.length; j++) {
          matrix[0][j] = j;
        }

        for (let i = 1; i <= b.length; i++) {
          for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
              matrix[i][j] = matrix[i - 1][j - 1];
            } else {
              matrix[i][j] = Math.min(
                matrix[i - 1][j - 1] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j] + 1,
              );
            }
          }
        }

        return matrix[b.length][a.length];
      };

      const distance = getLevenshteinDistance(normalized1, normalized2);
      const maxLength = Math.max(normalized1.length, normalized2.length);
      return maxLength === 0 ? 1.0 : 1.0 - distance / maxLength;
    };

    const numberA = getNumber(titleA);
    const numberB = getNumber(titleB);

    // If both titles contain numbers and similarity is high enough (>= 0.8), sort by number
    if (numberA !== null && numberB !== null) {
      const similarity = calculateSimilarity(titleA, titleB);
      if (similarity >= 0.8) {
        return numberA - numberB;
      }
    }
  }

  // Default Chinese-Japanese-English friendly comparison
  // Use multiple locales for better cross-language sorting
  return titleA.localeCompare(titleB, ["zh-CN", "ja-JP", "en-US"], {
    numeric: true,
    ignorePunctuation: true,
    sensitivity: "base",
    usage: "sort",
  });
};

const setSortType = (type) => {
  if (sortType.value === type) {
    // If clicking the same sort type, toggle sort order
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    // If clicking different sort type, set new type and reset to ascending
    sortType.value = type;
    sortOrder.value = "asc";
  }

  // Save sort settings
  saveSortSettings();

  sortSearchResults();
};

const sortSearchResults = () => {
  const sorted = [...originalSearchedVideos.value].sort((a, b) => {
    if (sortType.value === "date") {
      // Sort by date
      const dateA = a.date ? new Date(a.date) : null;
      const dateB = b.date ? new Date(b.date) : null;

      // Handle null values: put at end regardless of sort order
      if (!dateA && !dateB) {
        // If both dates are null, sort by original video title (using Japanese-English friendly comparison)
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      if (!dateA) return 1;
      if (!dateB) return -1;

      const comparison = dateA - dateB;
      if (comparison === 0) {
        // If dates are same, sort by original video title (using Japanese-English friendly comparison)
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      return sortOrder.value === "asc" ? comparison : -comparison;
    } else if (sortType.value === "translation") {
      // Sort by translation status (composite sort: translation status priority + chronological + title)
      // Translation status priority: 1 = 2 = 4 → 3 → 5 → null
      const getTranslationPriority = (status) => {
        if (status === null || status === undefined || status === "") return 4; // null has lowest priority
        if (status === 1 || status === 2 || status === 4) return 1; // 1, 2, 4 have highest priority
        if (status === 3) return 2; // 3 has medium priority
        if (status === 5) return 3; // 5 has lower priority
        return 4; // other cases get lowest priority
      };

      const priorityA = getTranslationPriority(a.translation_status);
      const priorityB = getTranslationPriority(b.translation_status);

      // First sort by translation status priority
      if (priorityA !== priorityB) {
        const priorityComparison = priorityA - priorityB;
        return sortOrder.value === "asc"
          ? priorityComparison
          : -priorityComparison;
      }

      // When translation status is same, sort chronologically (within same priority group)
      const dateA = a.date ? new Date(a.date) : null;
      const dateB = b.date ? new Date(b.date) : null;

      // Handle null values: within same priority group, null dates go last
      if (!dateA && !dateB) {
        // If both dates are null, sort by original video title (using Japanese-English friendly comparison)
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      if (!dateA) return 1;
      if (!dateB) return -1;

      // Within same translation status group, sort chronologically first
      const dateComparison = dateA - dateB;
      if (dateComparison !== 0) {
        return dateComparison; // Always sort chronologically (not affected by sortOrder)
      }

      // When both translation status and date are same, sort by title as third-level sorting
      const titleA = a.original_name || "";
      const titleB = b.original_name || "";
      return compareVideoTitles(titleA, titleB);
    } else if (sortType.value === "relevance") {
      // Sort by backend relevance: use the original order from search API
      // The backend already sorts by relevance_score, series_priority, date, and id
      // So we preserve the original order when relevance sorting is selected
      const indexA = originalSearchedVideos.value.findIndex(
        (v) => v.id === a.id,
      );
      const indexB = originalSearchedVideos.value.findIndex(
        (v) => v.id === b.id,
      );

      // Sort by original API order (relevance-based)
      const comparison = indexA - indexB;
      return sortOrder.value === "asc" ? comparison : -comparison;
    }

    return 0;
  });

  searchedVideos.value = sorted;
};

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
    case 1:
      return "status-full"; // Chinese embedded - complete translation
    case 2:
      return "status-full"; // CC subtitles - complete translation
    case 3:
      return "status-partial"; // Danmaku translation - partial translation
    case 4:
      return "status-full"; // No translation needed - considered complete
    case 5:
      return "status-none"; // No translation - no translation
    default:
      return "status-unknown";
  }
};

// Navigate to author detail page with proper routing
const goToAuthor = (authorId, authorName) => {
  router.push(`/author/${authorId}`);
};

// Open external URL in new tab with security measures
const openUrl = (url) => {
  if (url) {
    // Ensure URL has protocol prefix for security
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};

// Helper functions for author data handling with priority rules
const getDisplayName = (author) => {
  if (!author) return "Unknown";
  return author.yt_name || author.nico_name || author.twitter_name || "Unknown";
};

const getDisplayUrl = (author) => {
  if (!author) return null;
  return author.yt_url || author.nico_url || author.twitter_url;
};

const getDisplayAvatar = (author) => {
  if (!author) return null;
  return author.nico_avatar || author.yt_avatar || author.twitter_avatar;
};

// Helper functions for video author data handling with priority rules
const getVideoAuthorName = (video) => {
  if (!video) return "Unknown";
  return video.yt_name || video.nico_name || video.twitter_name || "Unknown";
};

const getVideoAuthorAvatar = (video) => {
  if (!video) return null;
  return video.nico_avatar || video.yt_avatar || video.twitter_avatar;
};

// Helper function for Chinese-Japanese-English friendly text normalization
const normalizeTextForSearch = (text) => {
  if (!text) return "";

  // Convert to lowercase and normalize Unicode
  let normalized = text.toLowerCase().normalize("NFD");

  // Remove common CJK and Western punctuation and symbols
  normalized = normalized.replace(/[・･｜·]/g, " "); // Replace middle dots with space
  normalized = normalized.replace(/[「」『』【】〔〕〈〉《》（）()]/g, ""); // Remove brackets
  normalized = normalized.replace(/[！？｡､。，、]/g, ""); // Remove CJK punctuation
  normalized = normalized.replace(/[~～]/g, ""); // Remove tilde variations
  normalized = normalized.replace(/['"'""`]/g, ""); // Remove quote marks
  normalized = normalized.replace(/[＃#％%]/g, ""); // Remove symbols
  normalized = normalized.replace(/[　\s]+/g, " ").trim(); // Normalize spacing (including full-width spaces)

  return normalized;
};

// Helper function to check if text matches search query with Chinese-Japanese-English friendly comparison
const isTextMatch = (text, query) => {
  if (!text || !query) return false;

  const normalizedText = normalizeTextForSearch(text);
  const normalizedQuery = normalizeTextForSearch(query);

  // Direct substring match (highest priority)
  if (normalizedText.includes(normalizedQuery)) return true;

  // For short queries (1-2 characters), be more strict to avoid too many results
  if (query.length <= 2) {
    return normalizedText.includes(normalizedQuery);
  }

  // Script-aware segmentation for better CJK matching
  const getTextSegments = (text) => {
    const segments = [];

    // Split by spaces first
    segments.push(...text.split(/\s+/).filter((seg) => seg.length > 0));

    // Split by script boundaries (Hiragana/Katakana/Kanji/Latin)
    const scriptBoundaryPattern = /([ひ-ゟ]+|[ア-ヿ]+|[一-龯]+|[a-z0-9]+)/g;
    const scriptSegments = text.match(scriptBoundaryPattern) || [];
    segments.push(...scriptSegments);

    return [...new Set(segments)].filter((seg) => seg.length > 0);
  };

  // Word/segment-based matching for multi-part queries
  const querySegments = getTextSegments(normalizedQuery);
  const textSegments = getTextSegments(normalizedText);

  if (querySegments.length > 1) {
    // Check if most query segments are found in the text
    const foundSegments = querySegments.filter((querySegment) => {
      const isCJK = /[一-龯ひ-ゟア-ヿ]/.test(querySegment);
      const minLength = isCJK ? 1 : 2;

      if (querySegment.length < minLength) return false;

      return textSegments.some(
        (textSegment) =>
          textSegment.includes(querySegment) ||
          querySegment.includes(textSegment),
      );
    });

    // Consider it a match if at least 60% of meaningful segments are found
    const matchRatio = foundSegments.length / querySegments.length;
    return matchRatio >= 0.6;
  }

  // Partial matching for single segment queries
  if (querySegments.length === 1) {
    const querySegment = querySegments[0];
    const isCJK = /[一-龯ひ-ゟア-ヿ]/.test(querySegment);

    if (isCJK && querySegment.length === 1) {
      // For single CJK characters, require exact match in segments
      return textSegments.some((seg) => seg.includes(querySegment));
    } else if (querySegment.length >= 2) {
      // For longer segments, allow partial matching
      return textSegments.some(
        (seg) =>
          seg.includes(querySegment) ||
          querySegment.includes(seg) ||
          // Check if segments have significant overlap
          (seg.length >= 2 &&
            querySegment.length >= 2 &&
            (seg.includes(
              querySegment.substring(0, Math.min(3, querySegment.length)),
            ) ||
              querySegment.includes(
                seg.substring(0, Math.min(3, seg.length)),
              ))),
      );
    }
  }

  return false;
};

// Filter authors based on search query with Chinese-Japanese-English friendly fuzzy matching
const filteredAuthors = computed(() => {
  if (!searchQuery.value) return [];

  const query = searchQuery.value;
  return authors.value
    .filter((author) => {
      const ytName = author.yt_name || "";
      const nicoName = author.nico_name || "";
      const ytUrl = author.yt_url || "";
      const nicoUrl = author.nico_url || "";

      // Check name matches with Japanese-friendly comparison
      return (
        isTextMatch(ytName, query) ||
        isTextMatch(nicoName, query) ||
        isTextMatch(ytUrl, query) ||
        isTextMatch(nicoUrl, query)
      );
    })
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
    originalSearchedVideos.value = [];
    return;
  }

  try {
    const res = await fetch(
      `${API_URLS.SEARCH_VIDEOS}?q=${encodeURIComponent(query)}&limit=300`,
    );
    if (res.ok) {
      const results = await res.json();
      originalSearchedVideos.value = results;
      // Apply current sort settings to search results
      sortSearchResults();
    } else {
      searchedVideos.value = [];
      originalSearchedVideos.value = [];
    }
  } catch (error) {
    console.error("搜索视频失败:", error);
    searchedVideos.value = [];
    originalSearchedVideos.value = [];
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

/* Section header with title and sort controls */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

/* Section titles with underline */
.section-title {
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
  border-bottom: 2px solid #45475a;
  padding-bottom: 8px;
}

/* Override sort controls for inline usage in section header */
.section-header .sort-controls {
  padding: 0; /* Remove default padding from Sort.css */
  background-color: transparent; /* Remove background for inline usage */
  justify-content: flex-end; /* Keep right alignment in section header */
}

.section-header .sort-buttons {
  background: transparent; /* Remove glassmorphism background for inline usage */
  border: none; /* Remove border for cleaner inline appearance */
  padding: 0; /* Remove container padding */
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

  /* Section header responsive layout */
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
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
  /* Allow natural wrapping on mobile - section header can stack vertically */
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  /* Normal section title styling for mobile */
  .section-title {
    font-size: 1.2rem;
  }

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
