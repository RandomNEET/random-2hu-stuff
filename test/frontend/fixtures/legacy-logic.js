// Frozen pre-refactor behavior. Test-only; do not update when changing implementation.
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

const compareAuthorVideoTitles = (titleA, titleB) => {
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

const compareSearchVideoTitles = (titleA, titleB) => {
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

const paginationItems = (currentPage, totalPages, windowWidth) => {
  const current = currentPage;
  const total = totalPages;
  const items = [];

  // Decide display strategy based on screen size
  const isMobileView = windowWidth <= 768;
  const maxDisplayPages = isMobileView ? 5 : 9;
  const ellipsisThreshold = isMobileView ? 3 : 5;

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

  if (isMobileView) {
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
export {
  groupVideosByName,
  compareAuthorVideoTitles,
  compareSearchVideoTitles,
  normalizeTextForSearch,
  isTextMatch,
  paginationItems,
};

export const legacyHomeView = (items, filters, field, direction) => {
  const ref = (value) => ({ value });
  const authors = ref([]),
    videos = ref([]),
    searchedVideos = ref([]),
    groupedVideos = ref([]),
    currentPage = ref(1);
  const originalAuthors = ref(items),
    originalVideos = ref(items),
    originalSearchedVideos = ref(items);
  const authorFilters = ref(filters),
    videoFilters = ref(filters),
    sortBy = ref(field),
    sortType = ref(field),
    sortOrder = ref(direction);
  const updateUrlParams = () => {};
  const resolvedDuration = (video) =>
    video.original_duration ?? video.repost_duration;
  const getDisplayName = (author) =>
    author.yt_name || author.nico_name || author.twitter_name || "Unknown";
  const sortAuthors = () => {
    const f = authorFilters.value;
    const durationFilterActive =
      f.minAverageDuration !== null || f.maxAverageDuration !== null;
    const filtered = originalAuthors.value.filter((author) => {
      if (f.minWorks !== null && author.worksCount < f.minWorks) return false;
      if (f.maxWorks !== null && author.worksCount > f.maxWorks) return false;
      if (durationFilterActive) {
        if (
          author.averageDuration === null ||
          author.averageDuration === undefined
        ) {
          return f.includeUnknownDuration;
        }
        if (
          f.minAverageDuration !== null &&
          author.averageDuration < f.minAverageDuration
        )
          return false;
        if (
          f.maxAverageDuration !== null &&
          author.averageDuration > f.maxAverageDuration
        )
          return false;
      }
      return true;
    });
    const sorted = [...filtered].sort((a, b) => {
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
  sortAuthors();
  return authors.value;
};

export const legacyVideoView = (items, filters, field, direction) => {
  const ref = (value) => ({ value });
  const authors = ref([]),
    videos = ref([]),
    searchedVideos = ref([]),
    groupedVideos = ref([]),
    currentPage = ref(1);
  const originalAuthors = ref(items),
    originalVideos = ref(items),
    originalSearchedVideos = ref(items);
  const authorFilters = ref(filters),
    videoFilters = ref(filters),
    sortBy = ref(field),
    sortType = ref(field),
    sortOrder = ref(direction);
  const updateUrlParams = () => {};
  const resolvedDuration = (video) =>
    video.original_duration ?? video.repost_duration;
  const getDisplayName = (author) =>
    author.yt_name || author.nico_name || author.twitter_name || "Unknown";
  const sortVideos = (resetPage = true) => {
    const f = videoFilters.value;
    const durationFilterActive =
      f.minDuration !== null || f.maxDuration !== null;
    const filtered = originalVideos.value.filter((video) => {
      const duration = resolvedDuration(video);
      if (durationFilterActive) {
        if (duration === null || duration === undefined) {
          if (!f.includeUnknownDuration) return false;
        } else {
          if (f.minDuration !== null && duration < f.minDuration) return false;
          if (f.maxDuration !== null && duration > f.maxDuration) return false;
        }
      }
      if (
        f.translationStatus !== "all" &&
        String(video.translation_status) !== String(f.translationStatus)
      )
        return false;
      if (f.dateFrom && (!video.date || video.date < f.dateFrom)) return false;
      if (f.dateTo && (!video.date || video.date > f.dateTo)) return false;
      return true;
    });
    const sorted = [...filtered].sort((a, b) => {
      if (sortBy.value === "date") {
        const dateA = a.date ? new Date(a.date) : null;
        const dateB = b.date ? new Date(b.date) : null;

        if (!dateA && !dateB) {
          const titleA = a.original_name || "";
          const titleB = b.original_name || "";
          return compareAuthorVideoTitles(titleA, titleB);
        }
        if (!dateA) return 1;
        if (!dateB) return -1;

        const comparison = dateA - dateB;
        if (comparison === 0) {
          const titleA = a.original_name || "";
          const titleB = b.original_name || "";
          return compareAuthorVideoTitles(titleA, titleB);
        }
        return sortOrder.value === "asc" ? comparison : -comparison;
      } else if (sortBy.value === "translation") {
        const getTranslationPriority = (status) => {
          if (status === null || status === undefined || status === "")
            return 4;
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
  sortVideos();
  return videos.value;
};

export const legacySearchView = (items, filters, field, direction) => {
  const ref = (value) => ({ value });
  const authors = ref([]),
    videos = ref([]),
    searchedVideos = ref([]),
    groupedVideos = ref([]),
    currentPage = ref(1);
  const originalAuthors = ref(items),
    originalVideos = ref(items),
    originalSearchedVideos = ref(items);
  const authorFilters = ref(filters),
    videoFilters = ref(filters),
    sortBy = ref(field),
    sortType = ref(field),
    sortOrder = ref(direction);
  const updateUrlParams = () => {};
  const resolvedDuration = (video) =>
    video.original_duration ?? video.repost_duration;
  const getDisplayName = (author) =>
    author.yt_name || author.nico_name || author.twitter_name || "Unknown";
  const sortSearchResults = () => {
    const sorted = [...originalSearchedVideos.value].sort((a, b) => {
      if (sortType.value === "date") {
        const dateA = a.date ? new Date(a.date) : null;
        const dateB = b.date ? new Date(b.date) : null;

        if (!dateA && !dateB) {
          const titleA = a.original_name || "";
          const titleB = b.original_name || "";
          return compareSearchVideoTitles(titleA, titleB);
        }
        if (!dateA) return 1;
        if (!dateB) return -1;

        const comparison = dateA - dateB;
        if (comparison === 0) {
          const titleA = a.original_name || "";
          const titleB = b.original_name || "";
          return compareSearchVideoTitles(titleA, titleB);
        }
        return sortOrder.value === "asc" ? comparison : -comparison;
      } else if (sortType.value === "translation") {
        const getTranslationPriority = (status) => {
          if (status === null || status === undefined || status === "")
            return 4;
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
          return compareSearchVideoTitles(titleA, titleB);
        }
        if (!dateA) return 1;
        if (!dateB) return -1;

        const dateComparison = dateA - dateB;
        if (dateComparison !== 0) {
          return dateComparison;
        }

        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareSearchVideoTitles(titleA, titleB);
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
  sortSearchResults();
  return searchedVideos.value;
};
