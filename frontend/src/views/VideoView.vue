<template>
  <div class="video-list-container">
    <!-- Author information header -->
    <VideoAuthorHeader :author="author" :video-count="originalVideos.length" />

    <!-- Sort controls -->
    <VideoSortControls
      v-model:sort-by="sortBy"
      v-model:sort-order="sortOrder"
      @sort-change="handleSortChange"
    />

    <!-- Video list -->
    <div class="videos-grid">
      <VideoRow
        v-for="group in paginatedVideoGroups"
        :key="`group-${group.id}`"
        :group="group"
      />
    </div>

    <!-- Pagination -->
    <VideoPaginationControls
      v-if="totalPages > 1"
      v-model:current-page="currentPage"
      v-model:page-input="pageInput"
      :total-pages="totalPages"
      :window-width="9999"
      @jump-to-page="jumpToPage"
      @go-to-page="goToPage"
    />

    <!-- Back to top button -->
    <BackToTop />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { API_URLS, getApiUrl } from "@/config/api.js";
import VideoAuthorHeader from "@/components/VideoAuthorHeader.vue";
import VideoSortControls from "@/components/VideoSortControls.vue";
import VideoRow from "@/components/VideoRow.vue";
import VideoPaginationControls from "@/components/VideoPaginationControls.vue";
import BackToTop from "@/components/BackToTop.vue";

const route = useRoute();
const router = useRouter();
const videos = ref([]);
const originalVideos = ref([]);
const groupedVideos = ref([]);
const author = ref(null);

// Pagination related
const currentPage = ref(1);
const pageInput = ref("");
const itemsPerPage = 20;

// Load sort settings from URL query parameters first, then localStorage, finally use defaults
const getSavedSortSettings = () => {
  const urlSortBy = route.query.sortBy;
  const urlSortOrder = route.query.sortOrder;
  
  if (urlSortBy && (urlSortBy === 'date' || urlSortBy === 'translation')) {
    return {
      sortBy: urlSortBy,
      sortOrder: urlSortOrder === 'desc' ? 'desc' : 'asc',
    };
  }
  
  try {
    const saved = localStorage.getItem("videoList-sortSettings");
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        sortBy: parsed.sortBy || "translation",
        sortOrder: parsed.sortOrder || "asc",
      };
    }
  } catch (error) {
    console.warn("Failed to parse saved sort settings:", error);
  }
  return {
    sortBy: "translation",
    sortOrder: "asc",
  };
};

const savedSettings = getSavedSortSettings();
const sortBy = ref(savedSettings.sortBy);
const sortOrder = ref(savedSettings.sortOrder);

// Save sort settings to localStorage and URL
const saveSortSettings = () => {
  try {
    const settings = {
      sortBy: sortBy.value,
      sortOrder: sortOrder.value,
    };
    localStorage.setItem("videoList-sortSettings", JSON.stringify(settings));
    updateUrlParams();
  } catch (error) {
    console.warn("Failed to save sort settings:", error);
  }
};

// Update URL query parameters
const updateUrlParams = () => {
  const query = {};
  
  if (currentPage.value > 1) {
    query.page = currentPage.value.toString();
  }
  
  if (sortBy.value !== 'translation' || sortOrder.value !== 'asc') {
    query.sortBy = sortBy.value;
    query.sortOrder = sortOrder.value;
  }
  
  router.replace({ 
    path: route.path,
    query: query 
  }).catch(() => {});
};

// Handle sort change from VideoSortControls component
const handleSortChange = ({ sortBy: newSortBy, sortOrder: newSortOrder }) => {
  sortBy.value = newSortBy;
  sortOrder.value = newSortOrder;
  saveSortSettings();
  sortVideos(true);
};

// Helper function to get display name based on priority
const getDisplayName = (author) => {
  return author.yt_name || author.nico_name || author.twitter_name || "Unknown";
};

// Custom video title comparison function
const compareVideoTitles = (titleA, titleB) => {
  if (
    titleA.length === titleB.length &&
    titleA.length > 0 &&
    titleB.length > 0
  ) {
    const getNumber = (title) => {
      const arabicMatch = title.match(/[1-9]/);
      if (arabicMatch) {
        return parseInt(arabicMatch[0]);
      }

      const chineseNumbers = {
        一: 1, 二: 2, 三: 3, 四: 4, 五: 5,
        六: 6, 七: 7, 八: 8, 九: 9,
      };
      const chineseMatch = title.match(/[一二三四五六七八九]/);
      if (chineseMatch) {
        return chineseNumbers[chineseMatch[0]];
      }

      return null;
    };

    const calculateSimilarity = (str1, str2) => {
      const normalize = (str) =>
        str.replace(/[1-9一二三四五六七八九]/g, "").trim();
      const normalized1 = normalize(str1);
      const normalized2 = normalize(str2);

      if (normalized1 === normalized2) return 1.0;

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

    if (numberA !== null && numberB !== null) {
      const similarity = calculateSimilarity(titleA, titleB);
      if (similarity >= 0.8) {
        return numberA - numberB;
      }
    }
  }

  return titleA.localeCompare(titleB, ["ja-JP", "en-US"], {
    numeric: true,
    ignorePunctuation: true,
    sensitivity: "base",
  });
};

const sortVideos = (resetPage = true) => {
  const sorted = [...originalVideos.value].sort((a, b) => {
    if (sortBy.value === "date") {
      const dateA = a.date ? new Date(a.date) : null;
      const dateB = b.date ? new Date(b.date) : null;

      if (!dateA && !dateB) {
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      if (!dateA) return 1;
      if (!dateB) return -1;

      const comparison = dateA - dateB;
      if (comparison === 0) {
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      return sortOrder.value === "asc" ? comparison : -comparison;
    } else if (sortBy.value === "translation") {
      const getTranslationPriority = (status) => {
        if (status === null || status === undefined || status === "") return 4;
        if (status === 1 || status === 2 || status === 4) return 1;
        if (status === 3) return 2;
        if (status === 5) return 3;
        return 4;
      };

      const priorityA = getTranslationPriority(a.translation_status);
      const priorityB = getTranslationPriority(b.translation_status);

      if (priorityA !== priorityB) {
        const priorityComparison = priorityA - priorityB;
        return sortOrder.value === "asc"
          ? priorityComparison
          : -priorityComparison;
      }

      const dateA = a.date ? new Date(a.date) : null;
      const dateB = b.date ? new Date(b.date) : null;

      if (!dateA && !dateB) return 0;
      if (!dateA) return 1;
      if (!dateB) return -1;

      return dateA - dateB;
    }

    return 0;
  });

  videos.value = sorted;
  groupedVideos.value = groupVideosByName(sorted);

  if (resetPage) {
    currentPage.value = 1;
  }
  updateUrlParams();
};

// Group videos by original_url or repost_url
const groupVideosByName = (videoList) => {
  const groups = [];
  const processedVideos = new Set();

  videoList.forEach((video) => {
    if (processedVideos.has(video.id)) return;

    const group = {
      id: video.id,
      date: video.date,
      comment: video.comment,
      type: "single",
      videos: [video],
      displayOriginal: null,
      displayRepost: null,
      additionalOriginals: [],
      additionalReposts: [],
    };

    if (video.original_url && video.original_url.trim()) {
      const sameOriginalVideos = videoList.filter(
        (v) =>
          !processedVideos.has(v.id) &&
          v.original_url === video.original_url &&
          v.id !== video.id,
      );

      if (sameOriginalVideos.length > 0) {
        group.type = "original_group";
        group.displayOriginal = video;
        group.additionalReposts = [video, ...sameOriginalVideos];

        processedVideos.add(video.id);
        sameOriginalVideos.forEach((v) => processedVideos.add(v.id));

        groups.push(group);
        return;
      }
    }

    if (video.repost_url && video.repost_url.trim()) {
      const sameRepostVideos = videoList.filter(
        (v) =>
          !processedVideos.has(v.id) &&
          v.repost_url === video.repost_url &&
          v.id !== video.id,
      );

      if (sameRepostVideos.length > 0) {
        group.type = "repost_group";
        group.displayRepost = video;
        group.additionalOriginals = [video, ...sameRepostVideos];

        processedVideos.add(video.id);
        sameRepostVideos.forEach((v) => processedVideos.add(v.id));

        groups.push(group);
        return;
      }
    }

    processedVideos.add(video.id);
    groups.push(group);
  });

  return groups;
};

// Pagination related computed properties
const totalPages = computed(() =>
  Math.ceil(groupedVideos.value.length / itemsPerPage),
);

const paginatedVideoGroups = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return groupedVideos.value.slice(start, end);
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

// Listen for URL query changes and sync to local state
watch(() => route.query, (newQuery) => {
  const urlPage = parseInt(newQuery.page) || 1;
  const urlSortBy = newQuery.sortBy || 'translation';
  const urlSortOrder = newQuery.sortOrder || 'asc';
  
  const pageChanged = urlPage !== currentPage.value;
  const sortChanged = urlSortBy !== sortBy.value || urlSortOrder !== sortOrder.value;
  
  if (pageChanged) {
    currentPage.value = urlPage;
  }
  
  if (sortChanged) {
    sortBy.value = urlSortBy;
    sortOrder.value = urlSortOrder;
    sortVideos(false);
  }
});

// Listen for page changes, scroll to top and update URL
watch(currentPage, (newPage, oldPage) => {
  if (newPage !== oldPage) {
    window.scrollTo(0, 0);
    updateUrlParams();
  }
});

onMounted(async () => {
  const urlPage = parseInt(route.query.page);
  if (urlPage && urlPage >= 1) {
    currentPage.value = urlPage;
  }

  const authorId = route.params.id;
  try {
    // Get author information
    const authorRes = await fetch(API_URLS.AUTHORS);
    if (authorRes.ok) {
      const authors = await authorRes.json();
      author.value = authors.find((a) => a.id == authorId);
    }

    // Get video list
    const res = await fetch(getApiUrl(`/api/author/${authorId}/videos`));
    if (!res.ok) throw new Error("请求失败");
    const videoData = await res.json();
    originalVideos.value = videoData;

    sortVideos(false);
  } catch (e) {
    videos.value = [];
    originalVideos.value = [];
    console.error(e);
  }
});
</script>

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

/* Video list */
.videos-grid {
  padding: 24px;
}

/* Responsive design */
@media (max-width: 834px) {
  .video-list-container {
    max-width: 95%;
    margin: 16px auto;
  }

  .videos-grid {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .videos-grid {
    padding: 12px;
  }
}
</style>
