<template>
  <div class="author-page">
    <!-- Sort controls -->
    <div class="sort-controls">
      <div class="sort-buttons">
        <v-btn
          :class="['sort-btn', { active: sortBy === 'name' }]"
          @click="setSortBy('name')"
          size="small"
          rounded="lg"
        >
          <v-icon size="16">mdi-sort-alphabetical-variant</v-icon>
          <span>名称</span>
          <v-icon v-if="sortBy === 'name'" size="14">
            {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
          </v-icon>
        </v-btn>

        <v-btn
          :class="['sort-btn', { active: sortBy === 'worksCount' }]"
          @click="setSortBy('worksCount')"
          size="small"
          rounded="lg"
        >
          <v-icon size="16">mdi-chart-bar</v-icon>
          <span>视频数</span>
          <v-icon v-if="sortBy === 'worksCount'" size="14">
            {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
          </v-icon>
        </v-btn>

        <v-btn
          :class="['sort-btn', { active: sortBy === 'lastUpdate' }]"
          @click="setSortBy('lastUpdate')"
          size="small"
          rounded="lg"
        >
          <v-icon size="16">mdi-clock-outline</v-icon>
          <span>最近更新</span>
          <v-icon v-if="sortBy === 'lastUpdate'" size="14">
            {{ sortOrder === "asc" ? "mdi-chevron-up" : "mdi-chevron-down" }}
          </v-icon>
        </v-btn>
      </div>
    </div>

    <div class="card-grid">
      <div
        v-for="author in paginatedAuthors"
        :key="author.id"
        class="card-item"
        @click="
          $router.push({
            path: `/author/${encodeURIComponent(getDisplayName(author))}`,
            query: { id: author.id },
          })
        "
      >
        <!-- Avatar as background -->
        <div
          class="avatar-background"
          :style="{
            backgroundImage: getDisplayAvatar(author)
              ? `url(${getDisplayAvatar(author)})`
              : 'none',
          }"
        ></div>

        <!-- Acrylic glass overlay -->
        <div class="acrylic-overlay"></div>

        <!-- External link button in top-left corner -->
        <div
          v-if="getDisplayUrl(author)"
          class="url-button-container"
          @mouseenter="hoveredAuthorId = author.id"
          @mouseleave="hoveredAuthorId = null"
        >
          <v-btn
            icon
            size="small"
            class="url-button-top-left"
            @click.stop="handleUrlClick(author)"
            :title="
              hasMultipleUrls(author)
                ? '访问作者频道'
                : `访问${
                    author.yt_url 
                      ? 'YouTube' 
                      : author.nico_url 
                        ? 'NicoNico' 
                        : author.twitter_url 
                          ? 'Twitter'
                          : '作者'
                  }频道`
            "
          >
            <v-icon size="16">mdi-open-in-new</v-icon>
          </v-btn>

          <!-- Show platform-specific buttons when hovering and has multiple URLs -->
          <div
            v-if="hasMultipleUrls(author) && hoveredAuthorId === author.id"
            class="platform-buttons"
          >
            <v-btn
              v-if="author.yt_url"
              icon
              size="small"
              class="platform-btn youtube-btn"
              @click.stop="openSpecificUrl(author.yt_url)"
              title="YouTube频道"
            >
              <v-icon size="14">mdi-youtube</v-icon>
            </v-btn>
            <v-btn
              v-if="author.nico_url"
              icon
              size="small"
              class="platform-btn nico-btn"
              @click.stop="openSpecificUrl(author.nico_url)"
              title="NicoNico频道"
            >
              <img
                src="https://www.nicovideo.jp/favicon.ico"
                alt="NicoNico"
                style="width: 14px; height: 14px"
              />
            </v-btn>
            <v-btn
              v-if="author.twitter_url"
              icon
              size="small"
              class="platform-btn twitter-btn"
              @click.stop="openSpecificUrl(author.twitter_url)"
              title="Twitter频道"
            >
              <v-icon size="14">mdi-twitter</v-icon>
            </v-btn>
          </div>
        </div>

        <!-- Info section in center -->
        <div class="info-section">
          <div class="name">{{ getDisplayName(author) }}</div>
        </div>

        <!-- Video count in bottom-right corner -->
        <div class="works">📊 {{ author.worksCount }} 视频</div>
      </div>
    </div>

    <!-- Pagination - desktop only -->
    <div
      class="pagination-container desktop-only"
      v-if="totalPages > 1 && !isMobile"
    >
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

<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from "vue";
import { API_URLS } from "@/config/api.js";
import "@/assets/styles/Sort.css";
import "@/assets/styles/BackToTop.css";
import "@/assets/styles/Pagination.css";

const authors = ref([]);
const originalAuthors = ref([]); // Store original data
const currentPage = ref(1);
const pageInput = ref("");
const windowWidth = ref(window.innerWidth);
const showBackToTop = ref(false);
const cardsPerRow = ref(4); // Number of cards per row
const hoveredAuthorId = ref(null); // Track which author card is being hovered

// Load saved sort settings from localStorage, use defaults if none exist
const getSavedSortSettings = () => {
  try {
    const saved = localStorage.getItem("authorGrid-sortSettings");
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        sortBy: parsed.sortBy || "name",
        sortOrder: parsed.sortOrder || "asc",
      };
    }
  } catch (error) {
    console.warn("Failed to parse saved sort settings:", error);
  }
  return { sortBy: "name", sortOrder: "asc" };
};

const savedSettings = getSavedSortSettings();
const sortBy = ref(savedSettings.sortBy); // Sort field: name, worksCount, lastUpdate
const sortOrder = ref(savedSettings.sortOrder); // Sort order: asc, desc

// Save sort settings to localStorage
const saveSortSettings = () => {
  try {
    const settings = {
      sortBy: sortBy.value,
      sortOrder: sortOrder.value,
    };
    localStorage.setItem("authorGrid-sortSettings", JSON.stringify(settings));
  } catch (error) {
    console.warn("Failed to save sort settings:", error);
  }
};

// Detect if current viewport is mobile
const isMobile = computed(() => windowWidth.value <= 768);

// Sort related functions
const setSortBy = (field) => {
  if (sortBy.value === field) {
    // If clicking the same field, toggle sort order
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    // If clicking different field, set new field and use default sort
    sortBy.value = field;
    sortOrder.value = field === "name" ? "asc" : "desc"; // Name defaults to ascending, others to descending
  }

  // Save sort settings
  saveSortSettings();

  sortAuthors();
  currentPage.value = 1; // Reset to first page
};

// Helper function to get display name based on priority
const getDisplayName = (author) => {
  return author.yt_name || author.nico_name || author.twitter_name || "Unknown";
};

// Helper function to get display URL based on priority
const getDisplayUrl = (author) => {
  return author.yt_url || author.nico_url || author.twitter_url;
};

// Helper function to get display avatar based on priority
const getDisplayAvatar = (author) => {
  return author.nico_avatar || author.yt_avatar || author.twitter_avatar;
};

// Check if author has multiple URLs
const hasMultipleUrls = (author) => {
  if (!author) return false;
  const urlCount = [author.yt_url, author.nico_url, author.twitter_url].filter(Boolean).length;
  return urlCount > 1;
};

// Handle URL button click - direct navigation if only one URL
const handleUrlClick = (author) => {
  if (!hasMultipleUrls(author)) {
    const url = getDisplayUrl(author);
    if (url) {
      openUrl(url);
    }
  }
  // If has multiple URLs, do nothing on click - let hover handle it
};

// Open specific URL (YouTube or NicoNico)
const openSpecificUrl = (url) => {
  if (url) {
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};

const sortAuthors = () => {
  const sorted = [...originalAuthors.value].sort((a, b) => {
    let comparison = 0;

    switch (sortBy.value) {
      case "name":
        // Use Japanese-friendly sorting, supporting kana and kanji
        const nameA = getDisplayName(a);
        const nameB = getDisplayName(b);
        comparison = nameA.localeCompare(nameB, ["ja-JP", "zh-CN", "en-US"], {
          sensitivity: "base",
          numeric: true,
          ignorePunctuation: true,
        });
        break;
      case "worksCount":
        comparison = a.worksCount - b.worksCount;
        break;
      case "lastUpdate":
        const dateA = a.lastUpdate ? new Date(a.lastUpdate) : new Date(0);
        const dateB = b.lastUpdate ? new Date(b.lastUpdate) : new Date(0);
        comparison = dateA - dateB;
        break;
      default:
        comparison = 0;
    }

    return sortOrder.value === "asc" ? comparison : -comparison;
  });

  authors.value = sorted;
};

// Dynamically calculate cards per row - precisely match CSS Grid layout
const calculateCardsPerRow = () => {
  let calculatedCardsPerRow = 4; // Default value

  if (windowWidth.value <= 480) {
    // Mobile: fixed 2 per row - repeat(2, 1fr)
    calculatedCardsPerRow = 2;
  } else if (windowWidth.value <= 767) {
    // Large mobile/small tablet: fixed 3 per row - repeat(3, 1fr)
    calculatedCardsPerRow = 3;
  } else if (windowWidth.value <= 1199) {
    // Small desktop/tablet: fixed 4 per row - repeat(4, 1fr)
    calculatedCardsPerRow = 4;
  } else {
    // Large desktop: dynamic calculation - repeat(auto-fill, minmax(..., 1fr))
    let minCardWidth = 240; // Default minimum width
    let containerPadding = 48; // 24px * 2

    // Adjust parameters based on screen size to match CSS media queries
    if (windowWidth.value >= 1600) {
      // 4K large screen: minmax(220px, 1fr)
      minCardWidth = 220;
    } else if (windowWidth.value >= 1200) {
      // Medium desktop: minmax(200px, 1fr)
      minCardWidth = 200;
    }
    // Below 1200px uses default 240px

    // Calculate available width inside container
    const containerWidth = windowWidth.value - containerPadding;

    // CSS Grid auto-fill precise calculation logic
    const cardGap = 24;
    const maxPossibleCols = Math.floor(
      (containerWidth + cardGap) / (minCardWidth + cardGap),
    );

    // Ensure at least 4 columns, maximum 8 columns
    calculatedCardsPerRow = Math.max(4, Math.min(8, maxPossibleCols));

    // Debug information
    console.log(
      `窗口宽度: ${windowWidth.value}px, 最小卡片宽度: ${minCardWidth}px, 容器宽度: ${containerWidth}px, 计算列数: ${maxPossibleCols}, 最终列数: ${calculatedCardsPerRow}`,
    );
  }

  cardsPerRow.value = calculatedCardsPerRow;
};

// Responsive calculation of items per page - unified use of dynamic calculation × 8 rows
const itemsPerPage = computed(() => {
  // All pagination cases: cards per row × 8 rows
  return cardsPerRow.value * 8;
});

// Listen for window size changes
const handleResize = () => {
  windowWidth.value = window.innerWidth;
  // Recalculate cards per row
  calculateCardsPerRow();
  // If current page exceeds new total pages, adjust to last page
  if (currentPage.value > totalPages.value && totalPages.value > 0) {
    currentPage.value = totalPages.value;
  }
};

// Calculate pagination data
const totalPages = computed(() =>
  Math.ceil(authors.value.length / itemsPerPage.value),
);

const paginatedAuthors = computed(() => {
  // Mobile shows all authors, desktop uses pagination
  if (isMobile.value) {
    return authors.value;
  }

  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return authors.value.slice(start, end);
});

// Jump to specified page number
const goToPage = () => {
  const page = parseInt(pageInput.value);
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    pageInput.value = "";
  }
};

// Jump to specified page number (ellipsis click)
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

  // Decide display strategy based on screen size
  const isMobile = windowWidth.value <= 768;
  const maxDisplayPages = isMobile ? 5 : 9;
  const ellipsisThreshold = isMobile ? 3 : 5;

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

  if (isMobile) {
    // Mobile logic: maximum 5 elements (including ellipsis)
    if (showLeftEllipsis && showRightEllipsis) {
      // Both sides have ellipsis: 1 ... current ... total (5 elements)
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: Math.max(1, current - 1) });
      items.push({ type: "page", page: current });
      items.push({
        type: "ellipsis",
        targetPage: Math.min(total, current + 1),
      });
      items.push({ type: "page", page: total });
    } else if (showLeftEllipsis) {
      // Only left ellipsis: 1 ... current-1 current total (5 elements)
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: Math.max(1, current - 1) });
      if (current > total - 1) {
        items.push({ type: "page", page: total - 1 });
      } else {
        items.push({ type: "page", page: current - 1 });
      }
      items.push({ type: "page", page: current });
      items.push({ type: "page", page: total });
    } else if (showRightEllipsis) {
      // Only right ellipsis: 1 current current+1 ... total (5 elements)
      items.push({ type: "page", page: 1 });
      if (current === 1) {
        items.push({ type: "page", page: 2 });
        items.push({ type: "page", page: 3 });
      } else {
        items.push({ type: "page", page: current });
        items.push({ type: "page", page: current + 1 });
      }
      items.push({
        type: "ellipsis",
        targetPage: Math.min(total, current + 2),
      });
      items.push({ type: "page", page: total });
    } else {
      // No ellipsis: show all page numbers
      for (let i = 1; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    }
  } else {
    // Desktop logic: maintain original 9-page logic
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
  }

  return items;
};

// Back to top functionality
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

// Listen for scroll events to control back-to-top button visibility
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300;
};

// Listen for page changes, scroll to top (desktop only)
watch(currentPage, () => {
  if (!isMobile.value) {
    // window.scrollTo({ top: 0, behavior: "smooth" });
    window.scrollTo(0, 0);
  }
});

const openUrl = (url) => {
  if (url) {
    // Ensure URL has protocol prefix
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};

onMounted(async () => {
  // Add window resize listener
  window.addEventListener("resize", handleResize);
  // Add scroll event listener
  window.addEventListener("scroll", handleScroll);

  // Initial calculation of cards per row (all screen sizes)
  calculateCardsPerRow();

  const res = await fetch(API_URLS.AUTHORS);
  const data = await res.json();
  originalAuthors.value = data;

  // Initial sorting
  sortAuthors();
});

onUnmounted(() => {
  // Clean up event listeners
  window.removeEventListener("resize", handleResize);
  window.removeEventListener("scroll", handleScroll);
});
</script>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
  padding: 24px;
  background-color: #1e1e2e;
  /* Catppuccin Mocha Base */
  justify-content: center;
}

/* Responsive grid layout */
@media (min-width: 1600px) {
  /* 4K large screen: 7-9 per row */
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    max-width: 2200px;
    margin: 0 auto;
  }
}

@media (min-width: 1200px) and (max-width: 1599px) {
  /* Medium desktop: 5-6 per row */
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    max-width: 1400px;
    margin: 0 auto;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  /* Small desktop/tablet: 4 per row */
  .card-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    padding: 20px;
  }
}

@media (min-width: 481px) and (max-width: 767px) {
  /* Large mobile/small tablet: 3 per row */
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    padding: 16px;
  }
}

@media (max-width: 480px) {
  /* Mobile: 2 per row */
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    padding: 12px;
  }
}

.card-item {
  position: relative;
  aspect-ratio: 1;
  /* Square card layout */
  border-radius: 20px;
  /* Rounded corners */
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  /* Default background for cards without avatar */
  background: linear-gradient(
    135deg,
    #1e1e2e 0%,
    #313244 100%
  ); /* Catppuccin Mocha Base to Surface0 */
}

.card-item:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 16px 48px rgba(203, 166, 247, 0.4);
  border-color: rgba(203, 166, 247, 0.6); /* Brighter border on hover */
}

/* Avatar background */
.avatar-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: transform 0.3s ease;
}

.card-item:hover .avatar-background {
  transform: scale(1.1);
}

/* Acrylic glass overlay */
.acrylic-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(30, 30, 46, 0.4);
  /* Adjust transparency to ensure text readability */
  backdrop-filter: blur(4px) saturate(1.2);
  /* Reduce blur intensity */
  -webkit-backdrop-filter: blur(4px) saturate(1.2);
}

/* External link button in top-left corner */
.url-button-container {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.url-button-top-left {
  background-color: rgba(30, 30, 46, 0.9) !important;
  color: #89b4fa !important;
  /* Catppuccin Mocha Blue */
  transition: all 0.3s ease;
  backdrop-filter: blur(12px);
  border: 2px solid rgba(137, 180, 250, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.url-button-top-left:hover {
  background-color: rgba(137, 180, 250, 0.2) !important;
  color: #74c7ec !important;
  /* Catppuccin Mocha Sapphire */
  transform: scale(1.15);
  border-color: rgba(116, 199, 236, 0.6);
  box-shadow: 0 4px 20px rgba(137, 180, 250, 0.5);
}

/* Platform-specific buttons */
.platform-buttons {
  display: flex;
  flex-direction: row;
  gap: 8px;
  opacity: 0;
  transform: translateX(-10px);
  animation: slideInFade 0.3s ease-out forwards;
}

@keyframes slideInFade {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.platform-btn {
  background-color: rgba(30, 30, 46, 0.9) !important;
  color: #89b4fa !important;
  transition: all 0.3s ease;
  backdrop-filter: blur(12px);
  border: 2px solid rgba(137, 180, 250, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.platform-btn:hover {
  background-color: rgba(137, 180, 250, 0.2) !important;
  color: #74c7ec !important;
  transform: scale(1.15);
  border-color: rgba(116, 199, 236, 0.6);
  box-shadow: 0 4px 20px rgba(137, 180, 250, 0.5);
}

.youtube-btn {
  color: #ff0000 !important;
}

.youtube-btn:hover {
  color: #ff3333 !important;
}

.nico-btn {
  color: #ff6b00 !important;
}

.nico-btn:hover {
  color: #ff8533 !important;
}

.twitter-btn {
  color: #1da1f2 !important;
}

.twitter-btn:hover {
  color: #4db6f7 !important;
}

/* Info section styling - occupies entire card, centered display */
.info-section {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  z-index: 5;
  padding: 20px;
}

.name {
  font-weight: bold;
  font-size: 1.4rem;
  color: #f9e2af;
  /* Catppuccin Mocha Yellow */
  margin-bottom: 12px;
  line-height: 1.2;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
  /* Reduce text shadow */
}

.works {
  position: absolute;
  /* Position to bottom-right corner */
  bottom: 12px;
  right: 12px;
  color: #cba6f7;
  /* Catppuccin Mocha Mauve */
  font-size: 0.9rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(203, 166, 247, 0.15);
  /* Reduce background transparency */
  backdrop-filter: blur(4px);
  /* Reduce blur effect */
  border: 1px solid rgba(203, 166, 247, 0.3);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.5);
  /* Reduce text shadow */
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  /* Reduce shadow */
  z-index: 6;
}

/* Responsive text and element sizing */
@media (max-width: 768px) {
  .name {
    font-size: 1.1rem;
  }

  .works {
    font-size: 0.8rem;
    padding: 4px 8px;
    bottom: 8px;
    right: 8px;
  }

  .url-button-container {
    top: 8px;
    left: 8px;
  }

  .info-section {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .info-section {
    padding: 12px;
  }

  .url-button-container {
    top: 6px;
    left: 6px;
  }

  .name {
    font-size: 0.95rem;
  }

  .works {
    font-size: 0.75rem;
    padding: 4px 8px;
  }
}

/* Loading animation effect */
.card-item {
  animation: fadeInUp 0.6s ease-out forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Add staggered animation delay for different cards - play by row, max 8 rows */
.card-item {
  animation-delay: 0s; /* Default delay */
}

/* Mobile: 2 per row, max 8 rows */
@media (max-width: 480px) {
  .card-item:nth-child(1),
  .card-item:nth-child(2) {
    animation-delay: 0s;
  }
  .card-item:nth-child(3),
  .card-item:nth-child(4) {
    animation-delay: 0.1s;
  }
  .card-item:nth-child(5),
  .card-item:nth-child(6) {
    animation-delay: 0.2s;
  }
  .card-item:nth-child(7),
  .card-item:nth-child(8) {
    animation-delay: 0.3s;
  }
  .card-item:nth-child(9),
  .card-item:nth-child(10) {
    animation-delay: 0.4s;
  }
  .card-item:nth-child(11),
  .card-item:nth-child(12) {
    animation-delay: 0.5s;
  }
  .card-item:nth-child(13),
  .card-item:nth-child(14) {
    animation-delay: 0.6s;
  }
  .card-item:nth-child(15),
  .card-item:nth-child(16) {
    animation-delay: 0.7s;
  }
}

/* Large mobile/small tablet: 3 per row, max 8 rows */
@media (min-width: 481px) and (max-width: 767px) {
  .card-item:nth-child(1),
  .card-item:nth-child(2),
  .card-item:nth-child(3) {
    animation-delay: 0s;
  }
  .card-item:nth-child(4),
  .card-item:nth-child(5),
  .card-item:nth-child(6) {
    animation-delay: 0.1s;
  }
  .card-item:nth-child(7),
  .card-item:nth-child(8),
  .card-item:nth-child(9) {
    animation-delay: 0.2s;
  }
  .card-item:nth-child(10),
  .card-item:nth-child(11),
  .card-item:nth-child(12) {
    animation-delay: 0.3s;
  }
  .card-item:nth-child(13),
  .card-item:nth-child(14),
  .card-item:nth-child(15) {
    animation-delay: 0.4s;
  }
  .card-item:nth-child(16),
  .card-item:nth-child(17),
  .card-item:nth-child(18) {
    animation-delay: 0.5s;
  }
  .card-item:nth-child(19),
  .card-item:nth-child(20),
  .card-item:nth-child(21) {
    animation-delay: 0.6s;
  }
  .card-item:nth-child(22),
  .card-item:nth-child(23),
  .card-item:nth-child(24) {
    animation-delay: 0.7s;
  }
}

/* Small desktop/tablet: 4 per row, max 8 rows */
@media (min-width: 768px) and (max-width: 1199px) {
  .card-item:nth-child(1),
  .card-item:nth-child(2),
  .card-item:nth-child(3),
  .card-item:nth-child(4) {
    animation-delay: 0s;
  }
  .card-item:nth-child(5),
  .card-item:nth-child(6),
  .card-item:nth-child(7),
  .card-item:nth-child(8) {
    animation-delay: 0.1s;
  }
  .card-item:nth-child(9),
  .card-item:nth-child(10),
  .card-item:nth-child(11),
  .card-item:nth-child(12) {
    animation-delay: 0.2s;
  }
  .card-item:nth-child(13),
  .card-item:nth-child(14),
  .card-item:nth-child(15),
  .card-item:nth-child(16) {
    animation-delay: 0.3s;
  }
  .card-item:nth-child(17),
  .card-item:nth-child(18),
  .card-item:nth-child(19),
  .card-item:nth-child(20) {
    animation-delay: 0.4s;
  }
  .card-item:nth-child(21),
  .card-item:nth-child(22),
  .card-item:nth-child(23),
  .card-item:nth-child(24) {
    animation-delay: 0.5s;
  }
  .card-item:nth-child(25),
  .card-item:nth-child(26),
  .card-item:nth-child(27),
  .card-item:nth-child(28) {
    animation-delay: 0.6s;
  }
  .card-item:nth-child(29),
  .card-item:nth-child(30),
  .card-item:nth-child(31),
  .card-item:nth-child(32) {
    animation-delay: 0.7s;
  }
}

/* Medium desktop: dynamic per row count, max 8 rows */
@media (min-width: 1200px) and (max-width: 1599px) {
  .card-item:nth-child(-n + 6) {
    animation-delay: 0s;
  } /* Row 1: assume 6 per row */
  .card-item:nth-child(n + 7):nth-child(-n + 12) {
    animation-delay: 0.1s;
  } /* Row 2 */
  .card-item:nth-child(n + 13):nth-child(-n + 18) {
    animation-delay: 0.2s;
  } /* Row 3 */
  .card-item:nth-child(n + 19):nth-child(-n + 24) {
    animation-delay: 0.3s;
  } /* Row 4 */
  .card-item:nth-child(n + 25):nth-child(-n + 30) {
    animation-delay: 0.4s;
  } /* Row 5 */
  .card-item:nth-child(n + 31):nth-child(-n + 36) {
    animation-delay: 0.5s;
  } /* Row 6 */
  .card-item:nth-child(n + 37):nth-child(-n + 42) {
    animation-delay: 0.6s;
  } /* Row 7 */
  .card-item:nth-child(n + 43):nth-child(-n + 48) {
    animation-delay: 0.7s;
  } /* Row 8 */
}

/* 4K large screen: dynamic per row count, max 8 rows */
@media (min-width: 1600px) {
  .card-item:nth-child(-n + 8) {
    animation-delay: 0s;
  } /* Row 1: assume 8 per row */
  .card-item:nth-child(n + 9):nth-child(-n + 16) {
    animation-delay: 0.1s;
  } /* Row 2 */
  .card-item:nth-child(n + 17):nth-child(-n + 24) {
    animation-delay: 0.2s;
  } /* Row 3 */
  .card-item:nth-child(n + 25):nth-child(-n + 32) {
    animation-delay: 0.3s;
  } /* Row 4 */
  .card-item:nth-child(n + 33):nth-child(-n + 40) {
    animation-delay: 0.4s;
  } /* Row 5 */
  .card-item:nth-child(n + 41):nth-child(-n + 48) {
    animation-delay: 0.5s;
  } /* Row 6 */
  .card-item:nth-child(n + 49):nth-child(-n + 56) {
    animation-delay: 0.6s;
  } /* Row 7 */
  .card-item:nth-child(n + 57):nth-child(-n + 64) {
    animation-delay: 0.7s;
  } /* Row 8 */
}
</style>
