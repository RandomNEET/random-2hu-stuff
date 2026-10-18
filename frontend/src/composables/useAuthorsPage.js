import { selectAuthors } from "@/utils/selectAuthors.js";
import { fetchAuthors as fetchAuthorsResponse } from "@/services/api.js";
import {
  defaultAuthorFilters,
  queryValue,
  authorFiltersFromQuery as filtersFromQuery,
} from "@/utils/filters.js";
import { ref, onMounted, computed, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";

export function useAuthorsPage() {
  const route = useRoute();
  const router = useRouter();

  const authors = ref([]);
  const originalAuthors = ref([]); // Store original data
  const dataLoaded = ref(false);
  const showFilterEmpty = ref(false);
  let filterEmptyTimer;
  const currentPage = ref(1);
  const pageInput = ref("");
  const windowWidth = ref(window.innerWidth);
  const cardsPerRow = ref(4); // Number of cards per row

  const getSavedFilters = () => {
    const hasUrlFilters = [
      "minW",
      "maxW",
      "minDur",
      "maxDur",
      "unknown",
      "minWorks",
      "maxWorks",
      "minAvgDuration",
      "maxAvgDuration",
      "includeUnknownDuration",
    ].some((key) => route.query[key] !== undefined);
    if (hasUrlFilters) return filtersFromQuery(route.query);
    try {
      const saved = localStorage.getItem("authorGrid-filterSettings");
      if (saved) return { ...defaultAuthorFilters(), ...JSON.parse(saved) };
    } catch (error) {
      console.warn("Failed to parse saved author filters:", error);
    }
    return defaultAuthorFilters();
  };
  const authorFilters = ref(getSavedFilters());
  const maxWorks = computed(() =>
    Math.max(1, ...originalAuthors.value.map((a) => a.worksCount || 0)),
  );
  const maxAverageDuration = computed(() =>
    Math.max(1800, ...originalAuthors.value.map((a) => a.averageDuration || 0)),
  );
  const activeFilterCount = computed(() => {
    const f = authorFilters.value;
    const durationActive =
      f.minAverageDuration !== null || f.maxAverageDuration !== null;
    return (
      Number(f.minWorks !== null || f.maxWorks !== null) +
      Number(durationActive) +
      Number(durationActive && f.includeUnknownDuration)
    );
  });

  // Load sort settings from URL query parameters first, then localStorage, finally use defaults
  const getSavedSortSettings = () => {
    // First try to get from URL query parameters
    const urlSortBy = queryValue(route.query, "sort", "sortBy");
    const urlSortOrder = queryValue(route.query, "order", "sortOrder");

    if (urlSortBy && ["name", "worksCount", "lastUpdate"].includes(urlSortBy)) {
      return {
        sortBy: urlSortBy,
        sortOrder: urlSortOrder === "desc" ? "desc" : "asc",
      };
    }

    // Then try localStorage
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

  // Save sort settings to localStorage and URL
  const saveSortSettings = () => {
    try {
      const settings = {
        sortBy: sortBy.value,
        sortOrder: sortOrder.value,
      };
      localStorage.setItem("authorGrid-sortSettings", JSON.stringify(settings));

      // Update URL query parameters
      updateUrlParams();
    } catch (error) {
      console.warn("Failed to save sort settings:", error);
    }
  };

  // Update URL query parameters
  const updateUrlParams = () => {
    const query = {};

    // Only add page to URL if not on first page
    if (currentPage.value > 1) {
      query.page = currentPage.value.toString();
    }

    // Only add sort params if not default (name, asc)
    if (sortBy.value !== "name" || sortOrder.value !== "asc") {
      query.sort = sortBy.value;
      query.order = sortOrder.value;
    }

    const f = authorFilters.value;
    if (f.minWorks !== null) query.minW = String(f.minWorks);
    if (f.maxWorks !== null) query.maxW = String(f.maxWorks);
    if (f.minAverageDuration !== null)
      query.minDur = String(f.minAverageDuration);
    if (f.maxAverageDuration !== null)
      query.maxDur = String(f.maxAverageDuration);
    if (
      (f.minAverageDuration !== null || f.maxAverageDuration !== null) &&
      f.includeUnknownDuration
    ) {
      query.unknown = "1";
    }

    // Use router.replace to avoid adding to history
    router
      .replace({
        path: route.path,
        query: query,
      })
      .catch(() => {});
  };

  // Detect if current viewport is mobile
  const isMobile = computed(() => windowWidth.value <= 768);

  // Handle sort change from SortControls component
  const handleSortChange = ({ sortBy: newSortBy, sortOrder: newSortOrder }) => {
    sortBy.value = newSortBy;
    sortOrder.value = newSortOrder;

    // Save sort settings
    saveSortSettings();

    sortAuthors();
    currentPage.value = 1; // Reset to first page
    updateUrlParams();
  };

  const handleFilterApply = (filters) => {
    authorFilters.value = filters;
    localStorage.setItem("authorGrid-filterSettings", JSON.stringify(filters));
    currentPage.value = 1;
    sortAuthors();
    updateUrlParams();
  };

  const sortAuthors = () => {
    authors.value = selectAuthors(
      originalAuthors.value, authorFilters.value, sortBy.value, sortOrder.value,
    );
  };

  const scheduleFilterEmpty = () => {
    clearTimeout(filterEmptyTimer);
    showFilterEmpty.value = false;
    if (!dataLoaded.value || authors.value.length > 0) return;
    filterEmptyTimer = setTimeout(() => {
      showFilterEmpty.value = true;
    }, 1500);
  };

  watch(() => authors.value.length, scheduleFilterEmpty);

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
      // console.log(
      //   `窗口宽度: ${windowWidth.value}px, 最小卡片宽度: ${minCardWidth}px, 容器宽度: ${containerWidth}px, 计算列数: ${maxPossibleCols}, 最终列数: ${calculatedCardsPerRow}`,
      // );
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
      // URL will be updated by watch(currentPage)
    }
  };

  // Jump to specified page number (ellipsis click)
  const jumpToPage = (page) => {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page;
      // URL will be updated by watch(currentPage)
    }
  };

  // Listen for URL query changes and sync to local state
  watch(
    () => route.query,
    (newQuery, oldQuery) => {
      // Avoid infinite loop: only update if URL actually changed from external source
      const urlPage = parseInt(newQuery.page) || 1;
      const urlSortBy = queryValue(newQuery, "sort", "sortBy") || "name";
      const urlSortOrder = queryValue(newQuery, "order", "sortOrder") || "asc";
      const nextFilters = filtersFromQuery(newQuery);

      // Check if URL is different from current state (external change)
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
      authorFilters.value = nextFilters;
      sortAuthors();
    },
  );

  // Listen for page changes, scroll to top (desktop only) and update URL
  watch(currentPage, (newPage, oldPage) => {
    if (newPage !== oldPage) {
      if (!isMobile.value) {
        // window.scrollTo({ top: 0, behavior: "smooth" });
        window.scrollTo(0, 0);
      }
      // Update URL
      updateUrlParams();
    }
  });

  onMounted(async () => {
    // Add window resize listener
    window.addEventListener("resize", handleResize);

    // Initial calculation of cards per row (all screen sizes)
    calculateCardsPerRow();

    // Initialize currentPage from URL query parameter
    const urlPage = parseInt(route.query.page);
    if (urlPage && urlPage >= 1) {
      currentPage.value = urlPage;
    }

    const res = await fetchAuthorsResponse();
    const data = await res.json();
    originalAuthors.value = data;

    // Initial sorting
    sortAuthors();
    dataLoaded.value = true;
    scheduleFilterEmpty();

    // Update URL to reflect current state
    updateUrlParams();
  });

  onUnmounted(() => {
    // Clean up event listeners
    window.removeEventListener("resize", handleResize);
    clearTimeout(filterEmptyTimer);
  });

  return {
    showFilterEmpty,
    currentPage,
    pageInput,
    windowWidth,
    authorFilters,
    maxWorks,
    maxAverageDuration,
    activeFilterCount,
    sortBy,
    sortOrder,
    handleSortChange,
    handleFilterApply,
    totalPages,
    paginatedAuthors,
    goToPage,
    jumpToPage,
  };
}
