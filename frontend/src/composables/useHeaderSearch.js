import { getAuthorName } from "@/utils/authorDisplay.js";
import { translationOptions } from "@/utils/filters.js";
import { buildSearchQuery } from "@/utils/searchQuery.js";
import {
  fetchAuthors as fetchAuthorsResponse,
  fetchStats as fetchStatsResponse,
} from "@/services/api.js";
import {
  ref,
  computed,
  onMounted,
  watch,
  nextTick,
  onBeforeUnmount,
} from "vue";
import { useRouter } from "vue-router";

export function useHeaderSearch() {
  const router = useRouter();
  const showMobileSearch = ref(false);
  const showSearchPanel = ref(false);
  const searchContainer = ref(null);
  const shouldClearOnFocus = ref(false);
  const searchMaxDuration = ref(10800);

  // Search form data
  const searchForm = ref({
    query: "",
    type: "videos", // 'videos' or 'authors'
    limit: 100,
    filters: {
      authorInput: "",
      translationStatus: "all",
      dateFrom: "",
      dateTo: "",
      minDuration: null,
      maxDuration: null,
      includeUnknownDuration: false,
    },
  });
  const searchDurationActive = computed(
    () =>
      searchForm.value.filters.minDuration !== null ||
      searchForm.value.filters.maxDuration !== null,
  );
  const searchDurationValid = computed(() => {
    const { minDuration, maxDuration } = searchForm.value.filters;
    return (
      minDuration === null || maxDuration === null || minDuration <= maxDuration
    );
  });

  // Author options for filter (loaded from API)
  const authorOptions = ref([]);

  // Load authors for filter dropdown
  const loadAuthors = async () => {
    try {
      const response = await fetchAuthorsResponse();
      const authors = await response.json();
      authorOptions.value = authors.map((author) => ({
        id: author.id,
        name:
          getAuthorName(author),
      }));
    } catch (error) {
      console.error("Failed to load authors:", error);
    }
  };

  const loadDurationMaximum = async () => {
    try {
      const response = await fetchStatsResponse();
      const stats = await response.json();
      if (Number.isFinite(stats.maxVideoDuration) && stats.maxVideoDuration > 0) {
        searchMaxDuration.value = Math.max(1800, stats.maxVideoDuration);
      }
    } catch (error) {
      console.error("Failed to load duration maximum:", error);
    }
  };

  // Clear query when mobile search overlay opens after a previous search
  watch(showMobileSearch, (isOpen) => {
    if (isOpen && shouldClearOnFocus.value) {
      searchForm.value.query = "";
      shouldClearOnFocus.value = false;
    }
  });

  // Watch for search type changes to adjust limit
  watch(
    () => searchForm.value.type,
    (newType) => {
      if (newType === "authors" && searchForm.value.limit > 200) {
        searchForm.value.limit = 200;
      }
    },
  );

  // Watch for route changes to handle panel state
  watch(
    () => router.currentRoute.value,
    () => {
      // Close search panel when route changes (e.g., after search)
      if (showSearchPanel.value) {
        // Use nextTick to ensure the navigation completes first
        nextTick(() => {
          showSearchPanel.value = false;
        });
      }
    },
  );

  // Close search panel when clicking outside
  const handleClickOutside = (event) => {
    if (searchContainer.value && !searchContainer.value.contains(event.target)) {
      // Check if clicked element is part of a dropdown menu or overlay
      const isDropdownClick = event.target.closest(
        '.v-overlay, .v-menu, .v-select__content, .v-combobox__content, .v-list, .v-list-item, .v-overlay__content, [role="listbox"], [role="option"]',
      );
      // Also check if the target has any Japanese/Chinese characters (additional safety)
      const hasAsianText =
        event.target.textContent &&
        /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]/.test(
          event.target.textContent,
        );
      const isComboboxItem = event.target.closest(".v-combobox") !== null;

      if (!isDropdownClick && !(hasAsianText && isComboboxItem)) {
        showSearchPanel.value = false;
      }
    }
  };

  // Reset search form to defaults
  const resetForm = () => {
    searchForm.value.type = "videos";
    searchForm.value.limit = 100;
    searchForm.value.filters = {
      authorInput: "",
      translationStatus: "all",
      dateFrom: "",
      dateTo: "",
      minDuration: null,
      maxDuration: null,
      includeUnknownDuration: false,
    };
  };

  // Find author ID by name for searching
  const findAuthorIdByName = (authorName) => {
    if (!authorName) return null;
    // 精确匹配作者名称
    const author = authorOptions.value.find((a) => a.name === authorName);
    if (author) {
      return author.id;
    }
    // 如果没有精确匹配，尝试模糊匹配
    const fuzzyAuthor = authorOptions.value.find((a) => {
      const name = a.name.toLowerCase();
      const input = authorName.toLowerCase();
      return name.includes(input) || input.includes(name);
    });
    return fuzzyAuthor ? fuzzyAuthor.id : null;
  };

  // Perform search with filters
  const performSearch = () => {
    if (!searchForm.value.query.trim() || !searchDurationValid.value) return;

    const query = buildSearchQuery(searchForm.value, findAuthorIdByName);

    if (searchForm.value.type === "videos" && searchForm.value.filters.authorInput) {
      const authorId = findAuthorIdByName(searchForm.value.filters.authorInput);
      if (authorId) console.log("Found author ID:", authorId, "for name:", searchForm.value.filters.authorInput);
      else console.warn("Author not found:", searchForm.value.filters.authorInput);
    }

    console.log("Final search query:", query); // 调试信息

    // Open search results in a new tab
    const url = router.resolve({ path: "/search", query }).href;
    window.open(url, "_blank");

    // Close panel
    showSearchPanel.value = false;
    shouldClearOnFocus.value = true;
  };

  const handleMobileSearch = () => {
    if (!searchForm.value.query.trim() || !searchDurationValid.value) return;

    const query = buildSearchQuery(searchForm.value, findAuthorIdByName);

    // Open search results in a new tab
    const url = router.resolve({ path: "/search", query }).href;
    window.open(url, "_blank");

    // Close mobile search
    showMobileSearch.value = false;
    shouldClearOnFocus.value = true;
  };

  const resetMobileSearch = () => {
    searchForm.value = {
      query: "",
      type: "videos",
      limit: 100,
      filters: {
        authorInput: "",
        translationStatus: "all",
        dateFrom: "",
        dateTo: "",
        minDuration: null,
        maxDuration: null,
        includeUnknownDuration: false,
      },
    };
  };

  // Handle search input focus event
  const handleSearchFocus = () => {
    if (shouldClearOnFocus.value) {
      searchForm.value.query = "";
      shouldClearOnFocus.value = false;
    }
    showSearchPanel.value = true;
  };

  // Handle search input click event
  const handleSearchClick = () => {
    if (shouldClearOnFocus.value) {
      searchForm.value.query = "";
      shouldClearOnFocus.value = false;
    }
    showSearchPanel.value = true;
  };

  // Handle search input change event
  const handleSearchInput = () => {
    showSearchPanel.value = true;
  };

  // Handle author selection for desktop
  const handleAuthorSelection = (value) => {
    console.log("Desktop author selection changed:", value);
    searchForm.value.filters.authorInput = value;
    // If value is selected from dropdown (not manually typed), it should take immediate effect
    if (
      value &&
      typeof value === "string" &&
      authorOptions.value.some((author) => author.name === value)
    ) {
      // Value was selected from dropdown, close menu and make it active immediately
      nextTick(() => {
        // Force close any open menus
        const combobox = searchContainer.value?.querySelector(".v-combobox");
        if (combobox) {
          const input = combobox.querySelector("input");
          if (input) {
            input.blur();
          }
        }
      });
    }
  };

  // Handle desktop author blur event
  const handleAuthorBlur = (event) => {
    const value = event.target.value;
    console.log("Desktop author blur event:", value);
    searchForm.value.filters.authorInput = value;
  };

  // Handle author selection for mobile
  const handleMobileAuthorSelection = (value) => {
    console.log("Mobile author selection changed:", value);
    searchForm.value.filters.authorInput = value;
    // If value is selected from dropdown, close menu immediately
    if (
      value &&
      typeof value === "string" &&
      authorOptions.value.some((author) => author.name === value)
    ) {
      nextTick(() => {
        // Force close any open menus
        const mobilePopup = document.querySelector(".mobile-search-popup");
        if (mobilePopup) {
          const combobox = mobilePopup.querySelector(".v-combobox");
          if (combobox) {
            const input = combobox.querySelector("input");
            if (input) {
              input.blur();
            }
          }
        }
      });
    }
  };

  // Handle mobile author blur event
  const handleMobileAuthorBlur = (event) => {
    const value = event.target.value;
    console.log("Mobile author blur event:", value);
    searchForm.value.filters.authorInput = value;
  };

  // Setup click outside listener
  watch(showSearchPanel, (newValue) => {
    if (newValue) {
      nextTick(() => {
        // Calculate panel position based on search input
        const searchInput = searchContainer.value?.querySelector(".v-field");
        if (searchInput) {
          const rect = searchInput.getBoundingClientRect();
          const panel = searchContainer.value?.querySelector(".search-panel");
          if (panel) {
            const panelWidth = Math.min(560, window.innerWidth - 40);
            const centeredLeft = rect.left + rect.width / 2 - panelWidth / 2;
            panel.style.top = `${rect.bottom + 8}px`;
            panel.style.left = `${Math.max(20, Math.min(centeredLeft, window.innerWidth - panelWidth - 20))}px`;
            panel.style.width = `${panelWidth}px`;
          }
        }
        document.addEventListener("click", handleClickOutside);
      });
    } else {
      document.removeEventListener("click", handleClickOutside);
    }
  });

  // Load data on component mount
  onMounted(() => {
    loadAuthors();
    loadDurationMaximum();
  });

  // Cleanup on unmount
  onBeforeUnmount(() => {
    document.removeEventListener("click", handleClickOutside);
  });

  return {
    showMobileSearch,
    showSearchPanel,
    searchContainer,
    searchMaxDuration,
    searchForm,
    searchDurationActive,
    searchDurationValid,
    authorOptions,
    resetForm,
    performSearch,
    handleMobileSearch,
    resetMobileSearch,
    handleSearchFocus,
    handleSearchClick,
    handleSearchInput,
    handleAuthorSelection,
    handleAuthorBlur,
    handleMobileAuthorSelection,
    handleMobileAuthorBlur,
    translationOptions,
  };
}
