<template>
  <div class="search-container">
    <div class="search-content">
      <h1 class="search-title">搜索结果</h1>

      <div class="search-info" v-if="searchQuery">
        <p class="search-query">
          搜索关键词：<span class="query-text">"{{ searchQuery }}"</span>
        </p>
        <p class="search-stats">
          <span v-if="searchType === 'authors'"
            >找到 {{ filteredAuthors.length }} 个作者</span
          >
          <span v-else>找到 {{ searchedVideos.length }} 个视频</span>
        </p>
      </div>

      <!-- Video search results section -->
      <div
        v-if="searchType === 'videos' && searchedVideos.length > 0"
        class="results-section"
      >
        <div class="section-header">
          <h2 class="section-title">相关视频</h2>

          <!-- Sort controls -->
          <SearchSortControls
            v-model:sort-type="sortType"
            v-model:sort-order="sortOrder"
            @sort-change="handleSortChange"
          />
        </div>

        <div class="videos-list">
          <SearchVideoRow
            v-for="video in searchedVideos"
            :key="video.id"
            :video="video"
            @author-click="goToAuthor"
          />
        </div>
      </div>

      <!-- Author search results -->
      <div
        v-if="searchType === 'authors' && filteredAuthors.length > 0"
        class="results-section"
      >
        <h2 class="section-title">相关作者</h2>
        <SearchAuthorGrid :authors="filteredAuthors" />
      </div>

      <!-- Loading and no results states -->
      <SearchStates
        :is-loading="isSearching"
        :has-query="!!searchQuery"
        :has-results="hasResults"
      />
    </div>

    <!-- Back to top button -->
    <BackToTop />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { API_URLS } from "@/config/api.js";
import SearchSortControls from "@/components/SearchSortControls.vue";
import SearchVideoRow from "@/components/SearchVideoRow.vue";
import SearchAuthorGrid from "@/components/SearchAuthorGrid.vue";
import SearchStates from "@/components/SearchStates.vue";
import BackToTop from "@/components/BackToTop.vue";

const route = useRoute();
const router = useRouter();
const authors = ref([]);
const searchedVideos = ref([]);
const originalSearchedVideos = ref([]);
const searchQuery = ref("");
const isSearching = ref(false);

const searchType = computed(() => route.query.type || "videos");

// Sort settings
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
    sortType: "relevance",
    sortOrder: "asc",
  };
};

const savedSettings = getSavedSortSettings();
const sortType = ref(savedSettings.sortType);
const sortOrder = ref(savedSettings.sortOrder);

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

// Computed property for has results
const hasResults = computed(() => {
  if (searchType.value === 'authors') {
    return filteredAuthors.value.length > 0;
  }
  return searchedVideos.value.length > 0;
});

// Handle sort change
const handleSortChange = ({ sortType: newSortType, sortOrder: newSortOrder }) => {
  sortType.value = newSortType;
  sortOrder.value = newSortOrder;
  saveSortSettings();
  sortSearchResults();
};

// Helper function for video title comparison
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
        normalizeTextForSearch(str)
          .replace(/[1-9一二三四五六七八九]/g, "")
          .trim();
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

  return titleA.localeCompare(titleB, ["zh-CN", "ja-JP", "en-US"], {
    numeric: true,
    ignorePunctuation: true,
    sensitivity: "base",
    usage: "sort",
  });
};

// Sort search results
const sortSearchResults = () => {
  const sorted = [...originalSearchedVideos.value].sort((a, b) => {
    if (sortType.value === "date") {
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
    } else if (sortType.value === "translation") {
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

      if (!dateA && !dateB) {
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      if (!dateA) return 1;
      if (!dateB) return -1;

      const dateComparison = dateA - dateB;
      if (dateComparison !== 0) {
        return dateComparison;
      }

      const titleA = a.original_name || "";
      const titleB = b.original_name || "";
      return compareVideoTitles(titleA, titleB);
    } else if (sortType.value === "relevance") {
      const indexA = originalSearchedVideos.value.findIndex(
        (v) => v.id === a.id,
      );
      const indexB = originalSearchedVideos.value.findIndex(
        (v) => v.id === b.id,
      );

      const comparison = indexA - indexB;
      return sortOrder.value === "asc" ? comparison : -comparison;
    }

    return 0;
  });

  searchedVideos.value = sorted;
};

// Helper function for text normalization
const normalizeTextForSearch = (text) => {
  if (!text) return "";

  let normalized = text.toLowerCase().normalize("NFD");

  normalized = normalized.replace(/[・･｜·]/g, " ");
  normalized = normalized.replace(/[「」『』【】〔〕〈〉《》（）()]/g, "");
  normalized = normalized.replace(/[！？｡､。，、]/g, "");
  normalized = normalized.replace(/[~～]/g, "");
  normalized = normalized.replace(/['"'""`]/g, "");
  normalized = normalized.replace(/[＃#％%]/g, "");
  normalized = normalized.replace(/[　\s]+/g, " ").trim();

  return normalized;
};

// Helper function for text matching
const isTextMatch = (text, query) => {
  if (!text || !query) return false;

  const normalizedText = normalizeTextForSearch(text);
  const normalizedQuery = normalizeTextForSearch(query);

  if (normalizedText.includes(normalizedQuery)) return true;

  if (query.length <= 2) {
    return normalizedText.includes(normalizedQuery);
  }

  const getTextSegments = (text) => {
    const segments = [];
    segments.push(...text.split(/\s+/).filter((seg) => seg.length > 0));

    const scriptBoundaryPattern = /([ひ-ゟ]+|[ア-ヿ]+|[一-龯]+|[a-z0-9]+)/g;
    const scriptSegments = text.match(scriptBoundaryPattern) || [];
    segments.push(...scriptSegments);

    return [...new Set(segments)].filter((seg) => seg.length > 0);
  };

  const querySegments = getTextSegments(normalizedQuery);
  const textSegments = getTextSegments(normalizedText);

  if (querySegments.length > 1) {
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

    const matchRatio = foundSegments.length / querySegments.length;
    return matchRatio >= 0.6;
  }

  if (querySegments.length === 1) {
    const querySegment = querySegments[0];
    const isCJK = /[一-龯ひ-ゟア-ヿ]/.test(querySegment);

    if (isCJK && querySegment.length === 1) {
      return textSegments.some((seg) => seg.includes(querySegment));
    } else if (querySegment.length >= 2) {
      return textSegments.some(
        (seg) =>
          seg.includes(querySegment) ||
          querySegment.includes(seg) ||
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

// Filter authors based on search query
const filteredAuthors = computed(() => {
  if (!searchQuery.value || searchType.value !== "authors") return [];

  const query = searchQuery.value;
  return authors.value
    .filter((author) => {
      const ytName = author.yt_name || "";
      const nicoName = author.nico_name || "";
      const ytUrl = author.yt_url || "";
      const nicoUrl = author.nico_url || "";

      return (
        isTextMatch(ytName, query) ||
        isTextMatch(nicoName, query) ||
        isTextMatch(ytUrl, query) ||
        isTextMatch(nicoUrl, query)
      );
    })
    .sort((a, b) => b.worksCount - a.worksCount);
});

// Fetch authors data
const fetchAuthors = async () => {
  try {
    const res = await fetch(API_URLS.AUTHORS);
    authors.value = await res.json();
  } catch (error) {
    console.error("获取作者数据失败:", error);
  }
};

// Search videos
const searchVideos = async (query) => {
  if (!query) {
    searchedVideos.value = [];
    originalSearchedVideos.value = [];
    isSearching.value = false;
    return;
  }

  isSearching.value = true;

  try {
    const searchParams = new URLSearchParams({
      q: query,
      limit: route.query.limit || "100",
      ...(route.query.type && { type: route.query.type }),
      ...(route.query.author && { author: route.query.author }),
      ...(route.query.translationStatus &&
        route.query.translationStatus !== "all" && {
          translationStatus: route.query.translationStatus,
        }),
      ...(route.query.dateFrom && { dateFrom: route.query.dateFrom }),
      ...(route.query.dateTo && { dateTo: route.query.dateTo }),
    });

    const searchType = route.query.type || "videos";
    const apiUrl =
      searchType === "authors"
        ? API_URLS.SEARCH_AUTHORS
        : API_URLS.SEARCH_VIDEOS;

    console.log("Search URL:", `${apiUrl}?${searchParams.toString()}`);

    const res = await fetch(`${apiUrl}?${searchParams.toString()}`);
    if (res.ok) {
      const results = await res.json();

      if (searchType === "videos") {
        authors.value = [];
        originalSearchedVideos.value = results;
        sortSearchResults();
      } else {
        searchedVideos.value = [];
        originalSearchedVideos.value = [];
        authors.value = results;
      }
    } else {
      searchedVideos.value = [];
      originalSearchedVideos.value = [];
      if (searchType === "authors") {
        authors.value = [];
      }
    }
  } catch (error) {
    console.error("搜索视频失败:", error);
    searchedVideos.value = [];
    originalSearchedVideos.value = [];
  } finally {
    isSearching.value = false;
  }
};

// Perform search
const performSearch = (query) => {
  searchVideos(query);
};

// Navigate to author page
const goToAuthor = (authorId, authorName) => {
  router.push(`/author/${authorId}`);
};

onMounted(() => {
  const searchType = route.query.type || "videos";
  if (searchType === "authors") {
    fetchAuthors();
  }

  const initialQuery = route.query.q || "";
  searchQuery.value = initialQuery;
  if (initialQuery) {
    performSearch(initialQuery);
  }
});

watch(
  () => route.query,
  (newQuery) => {
    const query = newQuery.q || "";
    searchQuery.value = query;
    performSearch(query);
  },
  { deep: true },
);

watch(
  () => route.query.type,
  (newType) => {
    const searchType = newType || "videos";
    if (searchType === "videos") {
      authors.value = [];
    } else {
      searchedVideos.value = [];
      originalSearchedVideos.value = [];
      if (authors.value.length === 0) {
        fetchAuthors();
      }
    }
  },
);
</script>

<style scoped>
.search-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px;
  background: #1e1e2e;
  min-height: calc(100vh - 70px);
}

.search-content {
  background: #313244;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid #45475a;
}

.search-title {
  text-align: center;
  color: #f9e2af;
  font-size: 2.5rem;
  font-weight: bold;
  margin-bottom: 32px;
}

.search-info {
  text-align: center;
  margin-bottom: 32px;
  padding: 16px;
  background: #45475a;
  border-radius: 12px;
}

.search-query {
  color: #cdd6f4;
  font-size: 1.2rem;
  margin: 0 0 8px 0;
}

.query-text {
  color: #89b4fa;
  font-weight: bold;
}

.search-stats {
  color: #a6adc8;
  font-size: 1rem;
  margin: 0;
}

.results-section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.section-title {
  color: #cba6f7;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 20px 0;
  border-bottom: 2px solid #45475a;
  padding-bottom: 12px;
}

.videos-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

/* Responsive design */
@media (max-width: 834px) {
  .search-container {
    padding: 20px 16px;
  }

  .search-content {
    padding: 24px 20px;
  }

  .search-title {
    font-size: 2rem;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .section-title {
    font-size: 1.2rem;
  }
}
</style>
