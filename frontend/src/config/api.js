// API configuration file
// Centrally manage all API addresses for easy deployment and maintenance

export const API_CONFIG = {
  // Base API URL - modify this to switch between different backend servers
  BASE_URL: "https://random-2hu-stuff.randomneet.me",
  // BASE_URL: 'http://192.168.0.24:3000',

  // API endpoint paths
  ENDPOINTS: {
    AUTHORS: "/api/authors",
    VIDEOS: "/api/videos",
    SEARCH_VIDEOS: "/api/search/videos",
    SEARCH_AUTHORS: "/api/search/authors",
    STATS: "/api/stats",
  },
};

// Get complete API URL
// Usage: getApiUrl('/api/custom/endpoint')
export const getApiUrl = (endpoint) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Predefined common API URLs - use these constants directly
export const API_URLS = {
  AUTHORS: getApiUrl(API_CONFIG.ENDPOINTS.AUTHORS),
  VIDEOS: getApiUrl(API_CONFIG.ENDPOINTS.VIDEOS),
  SEARCH_VIDEOS: getApiUrl(API_CONFIG.ENDPOINTS.SEARCH_VIDEOS),
  SEARCH_AUTHORS: getApiUrl(API_CONFIG.ENDPOINTS.SEARCH_AUTHORS),
  STATS: getApiUrl(API_CONFIG.ENDPOINTS.STATS),
};
