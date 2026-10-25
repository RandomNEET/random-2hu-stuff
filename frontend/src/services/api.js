import { API_URLS, getApiUrl } from "@/config/api.js";

// Return the original Response; callers retain their existing status/error handling.
export const fetchAuthors = () => fetch(API_URLS.AUTHORS);
export const fetchStats = () => fetch(API_URLS.STATS);
export const fetchAuthorVideos = (authorId) =>
  fetch(getApiUrl(`/api/author/${authorId}/videos`));
export const fetchSearchResults = (type, params) =>
  fetch(
    `${type === "authors" ? API_URLS.SEARCH_AUTHORS : API_URLS.SEARCH_VIDEOS}?${params.toString()}`,
  );
