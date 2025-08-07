<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { API_URLS, getApiUrl, API_CONFIG } from "@/config/api.js";
import "@/assets/styles/Sort.css";
import "@/assets/styles/BackToTop.css";
import "@/assets/styles/Pagination.css";

const route = useRoute();
const videos = ref([]);
const originalVideos = ref([]); // Store original data
const author = ref(null);
const showBackToTop = ref(false);
const avatarLoaded = ref(false); // Avatar loading state

// Pagination related
const currentPage = ref(1);
const pageInput = ref("");
const itemsPerPage = 20; // Display 20 videos per page

// Load saved sort settings from localStorage, use defaults if none exist
const getSavedSortSettings = () => {
  try {
    const saved = localStorage.getItem("videoList-sortSettings");
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        sortType: parsed.sortType || "translation",
        sortOrder: parsed.sortOrder || "asc",
      };
    }
  } catch (error) {
    console.warn("Failed to parse saved sort settings:", error);
  }
  return {
    sortType: "translation", // Default sort by translation status
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
    localStorage.setItem("videoList-sortSettings", JSON.stringify(settings));
  } catch (error) {
    console.warn("Failed to save sort settings:", error);
  }
};

// Sort related functions
// Custom video title comparison function with Japanese-English friendly sorting
// and special numeric handling for titles with same length and containing numbers
const compareVideoTitles = (titleA, titleB) => {
  // If titles have same length and both contain numbers (1-9 or 一-九), check similarity for series detection
  if (titleA.length === titleB.length && titleA.length > 0 && titleB.length > 0) {
    const getNumber = (title) => {
      // Extract Arabic numbers (1-9)
      const arabicMatch = title.match(/[1-9]/);
      if (arabicMatch) {
        return parseInt(arabicMatch[0]);
      }
      
      // Extract Chinese numbers (一-九)
      const chineseNumbers = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9 };
      const chineseMatch = title.match(/[一二三四五六七八九]/);
      if (chineseMatch) {
        return chineseNumbers[chineseMatch[0]];
      }
      
      return null;
    };
    
    // Calculate title similarity (excluding numbers)
    const calculateSimilarity = (str1, str2) => {
      // Remove numbers and normalize titles for similarity comparison
      const normalize = (str) => str.replace(/[1-9一二三四五六七八九]/g, '').trim();
      const normalized1 = normalize(str1);
      const normalized2 = normalize(str2);
      
      // Simple similarity check: if normalized titles are identical or very similar
      if (normalized1 === normalized2) return 1.0;
      
      // Levenshtein distance for similarity calculation
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
                matrix[i - 1][j] + 1
              );
            }
          }
        }
        
        return matrix[b.length][a.length];
      };
      
      const distance = getLevenshteinDistance(normalized1, normalized2);
      const maxLength = Math.max(normalized1.length, normalized2.length);
      return maxLength === 0 ? 1.0 : 1.0 - (distance / maxLength);
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
  
  // Default Japanese-English friendly comparison
  return titleA.localeCompare(titleB, ['ja-JP', 'en-US'], { 
    numeric: true, 
    ignorePunctuation: true,
    sensitivity: 'base'
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

  sortVideos();
};

const sortVideos = () => {
  const sorted = [...originalVideos.value].sort((a, b) => {
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
      // Sort by translation status (composite sort: translation status priority + chronological)
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
      if (!dateA && !dateB) return 0;
      if (!dateA) return 1;
      if (!dateB) return -1;

      // Within same translation status group, always sort chronologically (not affected by sortOrder)
      return dateA - dateB;
    }

    return 0;
  });

  videos.value = sorted;

  // Reset pagination, go back to first page after re-sorting
  currentPage.value = 1;
};

// Pagination related computed properties
const totalPages = computed(() =>
  Math.ceil(originalVideos.value.length / itemsPerPage),
);

const paginatedVideos = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return videos.value.slice(start, end);
});

// Pagination related functions
const goToPage = () => {
  const page = parseInt(pageInput.value);
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    pageInput.value = "";
  }
};

const jumpToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
  }
};

// Get page items array (including page numbers and ellipsis)
const getPageItems = () => {
  const current = currentPage.value;
  const total = totalPages.value;
  const items = [];

  const maxDisplayPages = 9;
  const ellipsisThreshold = 5;

  // If total pages <= max display pages, show all page numbers
  if (total <= maxDisplayPages) {
    for (let i = 1; i <= total; i++) {
      items.push({ type: "page", page: i });
    }
    return items;
  }

  // Case when total pages > max display pages
  const showLeftEllipsis = current >= ellipsisThreshold;
  const showRightEllipsis = current <= total - (ellipsisThreshold - 1);

  if (showLeftEllipsis && showRightEllipsis) {
    // Both sides have ellipsis: 1 ... current-2 current-1 current current+1 current+2 ... total
    items.push({ type: "page", page: 1 });
    items.push({ type: "ellipsis", targetPage: current - 3 });
    for (let i = current - 2; i <= current + 2; i++) {
      items.push({ type: "page", page: i });
    }
    items.push({ type: "ellipsis", targetPage: current + 3 });
    items.push({ type: "page", page: total });
  } else if (showLeftEllipsis) {
    // Only left ellipsis: 1 ... current-2 current-1 current current+1 current+2 ... total
    items.push({ type: "page", page: 1 });
    items.push({ type: "ellipsis", targetPage: current - 3 });
    for (let i = current - 2; i <= total; i++) {
      items.push({ type: "page", page: i });
    }
  } else if (showRightEllipsis) {
    // Only right ellipsis: 1 2 3 4 5 current current+1 current+2 ... total
    for (let i = 1; i <= current + 2; i++) {
      items.push({ type: "page", page: i });
    }
    items.push({ type: "ellipsis", targetPage: current + 3 });
    items.push({ type: "page", page: total });
  } else {
    // No ellipsis: show all page numbers (this case is handled when total <= 9)
    for (let i = 1; i <= total; i++) {
      items.push({ type: "page", page: i });
    }
  }

  return items;
};

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

const openUrl = (url) => {
  if (url) {
    // Ensure URL has protocol prefix
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    
    // Check if we're on mobile
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (isMobile) {
      // On mobile, use location.href for direct app redirection
      window.location.href = fullUrl;
    } else {
      // For desktop, use window.open
      window.open(fullUrl, "_blank", "noopener,noreferrer");
    }
  }
};

// Back to top functionality
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

// Avatar loading handler functions
const handleAvatarLoad = () => {
  avatarLoaded.value = true;
};

const handleAvatarError = () => {
  avatarLoaded.value = false;
};

// Listen for scroll events to control back-to-top button visibility
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300;
};

// Thumbnail loading handlers
const handleThumbnailLoad = (event) => {
  event.target.style.opacity = "1";
  // Hide loading indicator
  const loadingElement = event.target.previousElementSibling;
  if (
    loadingElement &&
    loadingElement.classList.contains("thumbnail-loading")
  ) {
    loadingElement.style.display = "none";
  }
};

const handleThumbnailError = (event) => {
  event.target.style.display = "none";
  // Hide loading indicator, show error state
  const loadingElement = event.target.previousElementSibling;
  if (
    loadingElement &&
    loadingElement.classList.contains("thumbnail-loading")
  ) {
    loadingElement.innerHTML = '<span class="error-text">封面加载失败</span>';
    loadingElement.style.color = "#f38ba8";
  }
};

// Determine if image needs special loading attributes
const needsSpecialAttributes = (imageUrl) => {
  if (!imageUrl) return false;
  
  const lowerUrl = imageUrl.toLowerCase();
  
  // Bilibili image links
  if (lowerUrl.includes('hdslb.com')) {
    return true;
  }
  
  return false;
};

onMounted(async () => {
  // Add scroll event listener
  window.addEventListener("scroll", handleScroll);

  const authorId = route.query.id;
  try {
    // Get author information
    const authorRes = await fetch(API_URLS.AUTHORS);
    if (authorRes.ok) {
      const authors = await authorRes.json();
      author.value = authors.find((a) => a.id == authorId);
      // If author has avatar, try to preload it
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

    // Get video list
    const res = await fetch(getApiUrl(`/api/author/${authorId}/videos`));
    if (!res.ok) throw new Error("请求失败");
    const videoData = await res.json();
    originalVideos.value = videoData;

    // Initial sorting
    sortVideos();
  } catch (e) {
    videos.value = [];
    originalVideos.value = [];
    console.error(e);
  }
});

// Listen for page changes, scroll to top
watch(currentPage, () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
});

onUnmounted(() => {
  // Clean up event listeners
  window.removeEventListener("scroll", handleScroll);
});
</script>

<template>
  <div class="video-list-container">
    <!-- Author information header -->
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
        <div class="video-count">📊 {{ originalVideos.length }} 个视频</div>
      </div>
    </div>

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
            {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
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
            {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
          </v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Video list -->
    <div class="videos-grid">
      <div v-for="video in paginatedVideos" :key="video.id" class="video-row">
        <div class="video-info-row">
          <div class="video-date" v-if="video.date">
            📅 {{ formatDate(video.date) }}
          </div>

          <div class="video-comment" v-if="video.comment">
            {{ video.comment }}
          </div>
        </div>

        <div class="video-columns">
          <!-- Original video column -->
          <div
            class="video-column original-column"
            :class="{
              'clickable-column': video.original_url,
              'disabled-column': !video.original_url,
            }"
            @click="video.original_url && openUrl(video.original_url)"
          >
            <div class="original-header">
              <!-- Original video thumbnail -->
              <div class="video-thumbnail" v-if="video.original_thumbnail">
                <div class="thumbnail-loading">
                  <v-progress-circular
                    size="32"
                    width="3"
                    color="primary"
                    indeterminate
                  ></v-progress-circular>
                  <span class="loading-text">封面加载中...</span>
                </div>
                <img
                  :src="video.original_thumbnail"
                  :alt="video.original_name || '原视频'"
                  :referrerpolicy="needsSpecialAttributes(video.original_thumbnail) ? 'no-referrer' : null"
                  :crossorigin="needsSpecialAttributes(video.original_thumbnail) ? 'anonymous' : null"
                  @load="handleThumbnailLoad"
                  @error="handleThumbnailError"
                />
              </div>

              <h3 class="video-title">
                {{ video.original_name || "暂无原视频" }}
              </h3>

              <!-- Video source -->
              <div
                class="video-source"
                v-if="video.original_url && getVideoSource(video.original_url)"
              >
                <span :class="getVideoSource(video.original_url).class">
                  {{ getVideoSource(video.original_url).text }}
                </span>
              </div>
            </div>
          </div>

          <!-- Repost column -->
          <div
            class="video-column repost-column"
            :class="{
              'clickable-column': video.repost_url,
              'disabled-column': !video.repost_url,
            }"
            @click="video.repost_url && openUrl(video.repost_url)"
          >
            <div class="repost-header">
              <!-- Repost video thumbnail -->
              <div class="video-thumbnail" v-if="video.repost_thumbnail">
                <div class="thumbnail-loading">
                  <v-progress-circular
                    size="32"
                    width="3"
                    color="primary"
                    indeterminate
                  ></v-progress-circular>
                  <span class="loading-text">封面加载中...</span>
                </div>
                <img
                  :src="video.repost_thumbnail"
                  :alt="video.repost_name || '转载视频'"
                  :referrerpolicy="needsSpecialAttributes(video.repost_thumbnail) ? 'no-referrer' : null"
                  :crossorigin="needsSpecialAttributes(video.repost_thumbnail) ? 'anonymous' : null"
                  @load="handleThumbnailLoad"
                  @error="handleThumbnailError"
                />
              </div>

              <h3 class="video-title">
                {{ video.repost_name || "暂无转载" }}
              </h3>

              <!-- Translation status -->
              <div
                class="translation-status"
                v-if="
                  video.translation_status !== null &&
                  video.translation_status !== '' &&
                  getTranslationStatusText(video.translation_status)
                "
              >
                <span
                  :class="getTranslationStatusClass(video.translation_status)"
                >
                  {{ getTranslationStatusText(video.translation_status) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination-container" v-if="totalPages > 1">
      <div class="pagination-wrapper">
        <!-- Previous page button -->
        <v-btn
          v-if="currentPage > 1"
          icon
          size="small"
          class="nav-button"
          @click="currentPage--"
        >
          <v-icon>mdi-chevron-left</v-icon>
        </v-btn>

        <!-- Page number buttons -->
        <div class="page-numbers">
          <!-- Dynamic page display -->
          <template
            v-for="item in getPageItems()"
            :key="item.page || item.type"
          >
            <!-- Regular page number -->
            <v-btn
              v-if="item.type === 'page'"
              :class="['page-btn', { active: currentPage === item.page }]"
              @click="currentPage = item.page"
              size="small"
              rounded="xl"
            >
              {{ item.page }}
            </v-btn>

            <!-- Ellipsis -->
            <v-btn
              v-else-if="item.type === 'ellipsis'"
              class="ellipsis-btn"
              @click="jumpToPage(item.targetPage)"
              size="small"
              rounded="xl"
            >
              ...
            </v-btn>
          </template>
        </div>

        <!-- Next page button -->
        <v-btn
          v-if="currentPage < totalPages"
          icon
          size="small"
          class="nav-button"
          @click="currentPage++"
        >
          <v-icon>mdi-chevron-right</v-icon>
        </v-btn>

        <!-- Manual page input -->
        <div class="page-input-section">
          <span class="page-input-label">跳至</span>
          <v-text-field
            v-model="pageInput"
            type="number"
            :min="1"
            :max="totalPages"
            class="page-input"
            variant="outlined"
            density="compact"
            hide-details
            @keyup.enter="goToPage"
          ></v-text-field>
          <span class="page-unit-label">页</span>
        </div>
      </div>
    </div>

    <!-- Back to top button -->
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

/* Author information header */
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

/* Video list */
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

/* Remove entire row hover effect, change to individual column hover effects */

.video-date {
  font-size: 0.9rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  background: #585b70; /* Catppuccin Mocha Surface2 */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
}

.video-info-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.video-comment {
  font-size: 0.9rem;
  color: #f2cdcd; /* Catppuccin Mocha Flamingo */
  background: rgba(242, 205, 205, 0.15);
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
  border: 1px solid rgba(242, 205, 205, 0.3);
  font-style: italic;
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

/* Clickable column styles */
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

/* Non-clickable column styles */
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

.video-thumbnail {
  width: 100%;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  background: #585b70; /* Catppuccin Mocha Surface2 */
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  position: relative;
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
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  font-size: 0.9rem;
  text-align: center;
}

.error-text {
  color: #f38ba8; /* Catppuccin Mocha Red */
  font-size: 0.9rem;
  text-align: center;
}

.video-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition:
    transform 0.3s ease,
    opacity 0.3s ease;
  opacity: 0; /* Initially transparent */
  position: absolute;
  top: 0;
  left: 0;
}

.clickable-column:hover .video-thumbnail img {
  transform: scale(1.05);
}

.video-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: #cdd6f4; /* Catppuccin Mocha Text */
  line-height: 1.4;
  transition: all 0.2s ease;
}

/* Title color in clickable columns */
.clickable-column .video-title {
  color: #89b4fa; /* Catppuccin Mocha Blue */
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

/* Video source styles */
.source-youtube {
  color: #f38ba8; /* Catppuccin Mocha Red */
  background: rgba(243, 139, 168, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(243, 139, 168, 0.3);
}

.source-niconico {
  color: #fab387; /* Catppuccin Mocha Peach */
  background: rgba(250, 179, 135, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(250, 179, 135, 0.3);
}

.source-bilibili {
  color: #89b4fa; /* Catppuccin Mocha Blue */
  background: rgba(137, 180, 250, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(137, 180, 250, 0.3);
}

.source-twitter {
  color: #74c7ec; /* Catppuccin Mocha Sapphire */
  background: rgba(116, 199, 236, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(116, 199, 236, 0.3);
}

.source-other {
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  background: rgba(203, 166, 247, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(203, 166, 247, 0.3);
}

/* Responsive design */
@media (max-width: 834px) {
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
    grid-template-columns: 1fr 1fr; /* Keep two-column layout */
    gap: 12px; /* Reduce spacing for small screens */
  }

  .video-column {
    padding: 12px; /* Reduce padding */
  }

  .video-title {
    font-size: 0.95rem; /* Slightly reduce font size */
  }

  .video-thumbnail {
    height: 200px; /* Reduce thumbnail height on smaller screens */
  }

  .repost-header {
    gap: 8px;
  }

  .original-header {
    gap: 8px;
  }

  .video-info-row {
    flex-direction: column;
    align-items: flex-start;
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
    grid-template-columns: 1fr 1fr; /* Keep two columns even on ultra-small screens */
    gap: 8px; /* Further reduce spacing */
  }

  .video-column {
    padding: 8px; /* Smaller padding */
  }

  .video-title {
    font-size: 0.85rem; /* Smaller font to fit space */
    line-height: 1.3;
  }

  .video-thumbnail {
    height: 80px; /* Further reduce thumbnail height on smallest screens */
  }

  .status-none,
  .status-full,
  .status-partial,
  .status-unknown,
  .source-youtube,
  .source-niconico,
  .source-bilibili,
  .source-twitter,
  .source-other {
    font-size: 0.7rem; /* Status labels also get smaller fonts */
    padding: 2px 6px;
  }

  .video-comment {
    font-size: 0.8rem;
    padding: 4px 8px;
  }
}
</style>
