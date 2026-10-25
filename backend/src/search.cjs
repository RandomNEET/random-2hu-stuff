const Fuse = require("fuse.js");
const { videoKey, authorKey, createLinkIndex } = require("./search-links.cjs");
const { AsyncLruCache, CACHE_TTL } = require("./cache.cjs");
const {
  VIDEO_SEARCH_OPTIONS,
  AUTHOR_SEARCH_OPTIONS,
  TRANSLATION_STATUS,
} = require("./search-options.cjs");

function parseSearchFilters(query) {
  const number = (value) => {
    if (value === undefined || value === null || value === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  };
  return {
    author: query.author ? parseInt(query.author) : "all",
    dateFrom: query.dateFrom || null,
    dateTo: query.dateTo || null,
    translationStatus: query.translationStatus || "all",
    minDuration: number(query.minDuration),
    maxDuration: number(query.maxDuration),
    includeUnknownDuration: query.includeUnknownDuration === "1",
    limit: Math.min(parseInt(query.limit) || 100, 500),
  };
}

function filterVideos(videos, filters) {
  const status = parseInt(filters.translationStatus);
  const hasDuration =
    filters.minDuration !== null || filters.maxDuration !== null;
  return videos.filter((video) => {
    if (filters.author !== "all" && video.author !== filters.author)
      return false;
    if (filters.dateFrom && (!video.date || video.date < filters.dateFrom))
      return false;
    if (filters.dateTo && (!video.date || video.date > filters.dateTo))
      return false;
    if (
      filters.translationStatus !== "all" &&
      video.translation_status !== status
    )
      return false;
    if (hasDuration) {
      const duration = video.original_duration ?? video.repost_duration;
      if (duration === null || duration === undefined)
        return filters.includeUnknownDuration;
      if (filters.minDuration !== null && duration < filters.minDuration)
        return false;
      if (filters.maxDuration !== null && duration > filters.maxDuration)
        return false;
    }
    return true;
  });
}

function createSearchService(
  repository,
  { now = Date.now, FuseClass = Fuse } = {},
) {
  let current = null;
  let refreshing = null;

  async function snapshot() {
    if (current && now() < current.expiresAt) return current;
    if (refreshing) return refreshing;
    refreshing = Promise.all([
      repository.searchVideos(),
      repository.searchAuthors(),
    ])
      .then(([videos, authors]) => {
        // Publish data together only when both queries succeeded.
        current = {
          videos,
          authors,
          videoLinks: null,
          authorLinks: null,
          expiresAt: now() + CACHE_TTL,
          videoFuse: null,
          authorFuse: null,
          models: new AsyncLruCache({
            ttl: Infinity,
            maxEntries: 32,
            maxWeight: Math.max(1, videos.length * 2),
            weightOf: (model) => model.count,
            now,
          }),
        };
        return current;
      })
      .finally(() => {
        refreshing = null;
      });
    return refreshing;
  }

  function videoIndex(data, filters) {
    const { limit, ...criteria } = filters;
    const unfiltered =
      criteria.author === "all" &&
      !criteria.dateFrom &&
      !criteria.dateTo &&
      criteria.translationStatus === "all" &&
      criteria.minDuration === null &&
      criteria.maxDuration === null;
    if (unfiltered) {
      data.videoFuse ??= new FuseClass(data.videos, VIDEO_SEARCH_OPTIONS);
      return data.videoFuse;
    }
    const key = JSON.stringify(criteria);
    const cached = data.models.get(key);
    if (cached) return cached.fuse;
    const videos = filterVideos(data.videos, filters);
    const fuse = new FuseClass(videos, VIDEO_SEARCH_OPTIONS);
    data.models.set(key, { fuse, count: videos.length });
    return fuse;
  }

  // Positive limits can be applied before Fuse formats all the result objects.
  // Retain the existing Array.slice behavior for negative limits.
  function search(fuse, term, limit) {
    return limit >= 0
      ? fuse.search(term, { limit })
      : fuse.search(term).slice(0, limit);
  }

  return {
    async videos(term, filters) {
      const data = await snapshot();
      const key = videoKey(term);
      if (key)
        data.videoLinks ??= createLinkIndex(
          data.videos,
          ["original_url", "repost_url"],
          videoKey,
        );
      const results = key
        ? filterVideos(data.videoLinks.get(key) || [], filters)
            .slice(0, filters.limit)
            .map((item) => ({ item, score: 0 }))
        : search(videoIndex(data, filters), term, filters.limit);
      return results.map((result) => ({
        ...result.item,
        searchScore: result.score,
        translation_status_text:
          TRANSLATION_STATUS[result.item.translation_status] || "未知",
      }));
    },
    async authors(term, limit) {
      const data = await snapshot();
      const key = authorKey(term);
      let results;
      if (key) {
        data.authorLinks ??= createLinkIndex(
          data.authors,
          ["yt_url", "nico_url", "twitter_url"],
          authorKey,
        );
        results = (data.authorLinks.get(key) || [])
          .slice(0, limit)
          .map((item) => ({ item, score: 0 }));
      } else {
        data.authorFuse ??= new FuseClass(data.authors, AUTHOR_SEARCH_OPTIONS);
        results = search(data.authorFuse, term, limit);
      }
      return results.map((result) => ({
        ...result.item,
        searchScore: result.score,
        displayName:
          result.item.yt_name ||
          result.item.nico_name ||
          result.item.twitter_name ||
          "Unknown",
      }));
    },
  };
}

module.exports = { createSearchService, parseSearchFilters, filterVideos };
