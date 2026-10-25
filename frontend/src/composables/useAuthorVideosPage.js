import { selectAuthorVideos } from "@/utils/selectAuthorVideos.js";
import {
  fetchAuthors as fetchAuthorsResponse,
  fetchAuthorVideos,
} from "@/services/api.js";
import { groupVideosByName } from "@/utils/videoGroups.js";
import {
  defaultVideoFilters,
  queryValue,
  videoFiltersFromQuery as filtersFromQuery,
} from "@/utils/filters.js";
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

export function useAuthorVideosPage() {
  const route = useRoute();
  const router = useRouter();
  const videos = ref([]);
  const originalVideos = ref([]);
  const groupedVideos = ref([]);
  const author = ref(null);
  const dataLoaded = ref(false);
  const showFilterEmpty = ref(false);
  let filterEmptyTimer;

  // Pagination related
  const currentPage = ref(1);
  const pageInput = ref("");
  const itemsPerPage = 20;

  const getSavedFilters = () => {
    const keys = [
      "minDur",
      "maxDur",
      "status",
      "from",
      "to",
      "unknown",
      "minDuration",
      "maxDuration",
      "translationStatus",
      "dateFrom",
      "dateTo",
      "includeUnknownDuration",
    ];
    if (keys.some((key) => route.query[key] !== undefined))
      return filtersFromQuery(route.query);
    try {
      const saved = localStorage.getItem("videoList-filterSettings");
      if (saved) return { ...defaultVideoFilters(), ...JSON.parse(saved) };
    } catch (error) {
      console.warn("Failed to parse saved video filters:", error);
    }
    return defaultVideoFilters();
  };
  const videoFilters = ref(getSavedFilters());
  const resolvedDuration = (video) =>
    video.original_duration ?? video.repost_duration;
  const maxVideoDuration = computed(() =>
    Math.max(
      1800,
      ...originalVideos.value.map((video) => resolvedDuration(video) || 0),
    ),
  );
  const activeFilterCount = computed(() => {
    const f = videoFilters.value;
    const durationActive = f.minDuration !== null || f.maxDuration !== null;
    return (
      Number(durationActive) +
      Number(f.translationStatus !== "all") +
      Number(!!f.dateFrom || !!f.dateTo) +
      Number(durationActive && f.includeUnknownDuration)
    );
  });

  // Load sort settings from URL query parameters first, then localStorage, finally use defaults
  const getSavedSortSettings = () => {
    const urlSortBy = queryValue(route.query, "sort", "sortBy");
    const urlSortOrder = queryValue(route.query, "order", "sortOrder");

    if (urlSortBy && (urlSortBy === "date" || urlSortBy === "translation")) {
      return {
        sortBy: urlSortBy,
        sortOrder: urlSortOrder === "desc" ? "desc" : "asc",
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

    if (sortBy.value !== "translation" || sortOrder.value !== "asc") {
      query.sort = sortBy.value;
      query.order = sortOrder.value;
    }

    const f = videoFilters.value;
    if (f.minDuration !== null) query.minDur = String(f.minDuration);
    if (f.maxDuration !== null) query.maxDur = String(f.maxDuration);
    if (f.translationStatus !== "all") query.status = f.translationStatus;
    if (f.dateFrom) query.from = f.dateFrom;
    if (f.dateTo) query.to = f.dateTo;
    if (
      (f.minDuration !== null || f.maxDuration !== null) &&
      f.includeUnknownDuration
    ) {
      query.unknown = "1";
    }

    router
      .replace({
        path: route.path,
        query: query,
      })
      .catch(() => {});
  };

  // Handle sort change from VideoSortControls component
  const handleSortChange = ({ sortBy: newSortBy, sortOrder: newSortOrder }) => {
    sortBy.value = newSortBy;
    sortOrder.value = newSortOrder;
    saveSortSettings();
    sortVideos(true);
  };

  const handleFilterApply = (filters) => {
    videoFilters.value = filters;
    localStorage.setItem("videoList-filterSettings", JSON.stringify(filters));
    sortVideos(true);
  };

  const sortVideos = (resetPage = true) => {
    const sorted = selectAuthorVideos(
      originalVideos.value,
      videoFilters.value,
      sortBy.value,
      sortOrder.value,
    );
    videos.value = sorted;
    groupedVideos.value = groupVideosByName(sorted);
    if (resetPage) currentPage.value = 1;
    updateUrlParams();
  };

  const scheduleFilterEmpty = () => {
    clearTimeout(filterEmptyTimer);
    showFilterEmpty.value = false;
    if (!dataLoaded.value || groupedVideos.value.length > 0) return;
    filterEmptyTimer = setTimeout(() => {
      showFilterEmpty.value = true;
    }, 1500);
  };

  watch(() => groupedVideos.value.length, scheduleFilterEmpty);

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
  watch(
    () => route.query,
    (newQuery) => {
      const urlPage = parseInt(newQuery.page) || 1;
      const urlSortBy = queryValue(newQuery, "sort", "sortBy") || "translation";
      const urlSortOrder = queryValue(newQuery, "order", "sortOrder") || "asc";
      const nextFilters = filtersFromQuery(newQuery);

      const pageChanged = urlPage !== currentPage.value;
      const sortChanged =
        urlSortBy !== sortBy.value || urlSortOrder !== sortOrder.value;

      if (pageChanged) {
        currentPage.value = urlPage;
      }

      if (sortChanged) {
        sortBy.value = urlSortBy;
        sortOrder.value = urlSortOrder;
      }
      videoFilters.value = nextFilters;
      sortVideos(false);
    },
  );

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
      const authorRes = await fetchAuthorsResponse();
      if (authorRes.ok) {
        const authors = await authorRes.json();
        author.value = authors.find((a) => a.id == authorId);
      }

      // Get video list
      const res = await fetchAuthorVideos(authorId);
      if (!res.ok) throw new Error("请求失败");
      const videoData = await res.json();
      originalVideos.value = videoData;

      sortVideos(false);
      dataLoaded.value = true;
      scheduleFilterEmpty();
    } catch (e) {
      videos.value = [];
      originalVideos.value = [];
      dataLoaded.value = true;
      scheduleFilterEmpty();
      console.error(e);
    }
  });

  onUnmounted(() => {
    clearTimeout(filterEmptyTimer);
  });

  return {
    videos,
    originalVideos,
    author,
    showFilterEmpty,
    currentPage,
    pageInput,
    videoFilters,
    maxVideoDuration,
    activeFilterCount,
    sortBy,
    sortOrder,
    handleSortChange,
    handleFilterApply,
    totalPages,
    paginatedVideoGroups,
    goToPage,
    jumpToPage,
  };
}
