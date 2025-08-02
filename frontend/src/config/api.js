// API 配置文件
// 在这里统一管理所有的 API 地址，方便部署和维护

export const API_CONFIG = {
  // 基础 API 地址 - 修改这里即可切换不同的后端服务器
  BASE_URL: 'https://random-2hu-stuff.randomneet.me',
  
  // API 端点路径
  ENDPOINTS: {
    AUTHORS: '/api/authors',
    VIDEOS: '/api/videos',
    SEARCH_VIDEOS: '/api/search/videos',
    STATS: '/api/stats'
  }
};

// 获取完整的 API URL
// 使用方法: getApiUrl('/api/custom/endpoint')
export const getApiUrl = (endpoint) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// 预定义的常用 API URLs - 直接使用这些常量
export const API_URLS = {
  AUTHORS: getApiUrl(API_CONFIG.ENDPOINTS.AUTHORS),
  VIDEOS: getApiUrl(API_CONFIG.ENDPOINTS.VIDEOS),
  SEARCH_VIDEOS: getApiUrl(API_CONFIG.ENDPOINTS.SEARCH_VIDEOS),
  STATS: getApiUrl(API_CONFIG.ENDPOINTS.STATS)
};

// 开发环境和生产环境的配置示例：
// 开发环境: 'http://192.168.0.29:3000'
// 生产环境: 'https://your-domain.com'
// 本地开发: 'http://localhost:3000'
