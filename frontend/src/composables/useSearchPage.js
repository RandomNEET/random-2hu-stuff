import { buildSearchParams } from "@/utils/searchQuery.js";
import { selectSearchVideos } from "@/utils/selectSearchVideos.js";
import {
  fetchAuthors as fetchAuthorsResponse,
  fetchSearchResults,
} from "@/services/api.js";
import { isTextMatch, isLinkSearch } from "@/utils/searchText.js";
import { groupVideosByName } from "@/utils/videoGroups.js";
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { API_URLS } from "@/config/api.js";

export function useSearchPage() {
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

  const groupedSearchedVideos = computed(() =>
    groupVideosByName(searchedVideos.value),
  );

  // Computed property for has results
  const hasResults = computed(() => {
    if (searchType.value === "authors") {
      return filteredAuthors.value.length > 0;
    }
    return searchedVideos.value.length > 0;
  });

  // Handle sort change
  const handleSortChange = ({
    sortType: newSortType,
    sortOrder: newSortOrder,
  }) => {
    sortType.value = newSortType;
    sortOrder.value = newSortOrder;
    saveSortSettings();
    sortSearchResults();
  };

  // Sort search results
  const sortSearchResults = () => {
    searchedVideos.value = selectSearchVideos(
      originalSearchedVideos.value,
      sortType.value,
      sortOrder.value,
    );
  };

  // Filter authors based on search query
  const filteredAuthors = computed(() => {
    if (!searchQuery.value || searchType.value !== "authors") return [];

    const query = searchQuery.value;
    return authors.value
      .filter((author) => {
        if (isLinkSearch(query)) return true;
        const ytName = author.yt_name || "";
        const nicoName = author.nico_name || "";
        const ytUrl = author.yt_url || "";
        const nicoUrl = author.nico_url || "";

        return (
          isTextMatch(ytName, query) ||
          isTextMatch(nicoName, query) ||
          isTextMatch(ytUrl, query) ||
          isTextMatch(nicoUrl, query) ||
          isTextMatch(author.twitter_name || "", query) ||
          isTextMatch(author.twitter_url || "", query)
        );
      })
      .sort((a, b) => b.worksCount - a.worksCount);
  });

  // Fetch authors data
  const fetchAuthors = async () => {
    try {
      const res = await fetchAuthorsResponse();
      const results = await res.json();
      if (!route.query.q && (route.query.type || "videos") === "authors") {
        authors.value = results;
      }
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
      const searchParams = buildSearchParams(query, route.query);

      const searchType = route.query.type || "videos";
      const apiUrl =
        searchType === "authors"
          ? API_URLS.SEARCH_AUTHORS
          : API_URLS.SEARCH_VIDEOS;

      console.log("Search URL:", `${apiUrl}?${searchParams.toString()}`);

      const res = await fetchSearchResults(searchType, searchParams);
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
    const url = router.resolve(`/author/${authorId}`).href;
    window.open(url, "_blank");
  };

  onMounted(() => {
    const searchType = route.query.type || "videos";
    if (searchType === "authors" && !route.query.q) {
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
        if (authors.value.length === 0 && !route.query.q) {
          fetchAuthors();
        }
      }
    },
  );

  return {
    searchedVideos,
    searchQuery,
    isSearching,
    searchType,
    sortType,
    sortOrder,
    groupedSearchedVideos,
    hasResults,
    handleSortChange,
    filteredAuthors,
    goToAuthor,
  };
}
