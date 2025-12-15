const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const cors = require("cors");
const Fuse = require("fuse.js");

const app = express();
app.use(cors());

// ============================================================================
// SEARCH CONFIGURATION - Fuzzy search using Fuse.js
// ============================================================================

// Fuse.js configuration for video search
const VIDEO_SEARCH_OPTIONS = {
  keys: [
    { name: 'original_name', weight: 0.7 },
    { name: 'repost_name', weight: 0.9 },
    { name: 'comment', weight: 0.3 }
  ],
  threshold: 0.4, // Lower = more strict matching
  distance: 100,
  includeScore: true,
  includeMatches: true,
  minMatchCharLength: 2,
  shouldSort: true,
  findAllMatches: false,
  ignoreLocation: true,
  ignoreFieldNorm: false
};

// Fuse.js configuration for author search
const AUTHOR_SEARCH_OPTIONS = {
  keys: [
    { name: 'yt_name', weight: 0.8 },
    { name: 'nico_name', weight: 0.8 },
    { name: 'twitter_name', weight: 0.8 }
  ],
  threshold: 0.3, // More strict for author names
  distance: 50,
  includeScore: true,
  includeMatches: true,
  minMatchCharLength: 1,
  shouldSort: true,
  findAllMatches: false,
  ignoreLocation: true
};

// Translation status mapping
const TRANSLATION_STATUS = {
  1: '中文内嵌',
  2: 'CC字幕',
  3: '弹幕翻译',
  4: '无需翻译',
  5: '暂无翻译'
};

// ============================================================================
// END OF SEARCH CONFIGURATION
// ============================================================================

// Optimize SQLite configuration for better performance
const db = new sqlite3.Database("./random-2hu-stuff.db", (err) => {
  if (err) {
    console.error('Error opening database:', err);
  } else {
    console.log('Connected to SQLite database');
    // Performance optimizations for SQLite
    db.run("PRAGMA journal_mode=WAL"); // Write-Ahead Logging for better concurrency
    db.run("PRAGMA synchronous=NORMAL"); // Balance between performance and safety
    db.run("PRAGMA cache_size=10000"); // Increase cache size for better read performance
    db.run("PRAGMA temp_store=MEMORY"); // Store temporary tables in memory
  }
});

// Simple in-memory cache implementation for API responses
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes cache duration

// Store data in cache with timestamp for TTL management
function setCache(key, data) {
  cache.set(key, {
    data,
    timestamp: Date.now()
  });
}

// Retrieve data from cache, checking TTL expiration
function getCache(key) {
  const item = cache.get(key);
  if (item && (Date.now() - item.timestamp) < CACHE_TTL) {
    return item.data;
  }
  // Remove expired cache entry
  cache.delete(key);
  return null;
}

// Periodic cache cleanup to prevent memory leaks
setInterval(() => {
  const now = Date.now();
  for (const [key, item] of cache.entries()) {
    if (now - item.timestamp > CACHE_TTL) {
      cache.delete(key);
    }
  }
}, 60000); // Clean up every minute

// GET /api/authors - Retrieve all authors with their video statistics
app.get("/api/authors", (req, res) => {
  const cacheKey = 'authors';
  const cached = getCache(cacheKey);
  
  // Return cached data if available and not expired
  if (cached) {
    return res.json(cached);
  }

  // SQL query to get authors with video count and last update date
  const query = `
    SELECT 
      a.id, 
      a.yt_name,
      a.yt_url,
      a.yt_avatar,
      a.nico_name,
      a.nico_url,
      a.nico_avatar,
      a.twitter_name,
      a.twitter_url,
      a.twitter_avatar,
      a.comment,
      COUNT(v.id) as worksCount,
      MAX(v.date) as lastUpdate
    FROM authors a
    LEFT JOIN videos v ON a.id = v.author
    GROUP BY a.id, a.yt_name, a.yt_url, a.yt_avatar, a.nico_name, a.nico_url, a.nico_avatar, a.twitter_name, a.twitter_url, a.twitter_avatar, a.comment
    ORDER BY COALESCE(a.yt_name, a.nico_name, a.twitter_name) ASC
  `;
  
  db.all(query, [], (err, rows) => {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    // Cache the results and send response
    setCache(cacheKey, rows);
    res.json(rows);
  });
});

// GET /api/author/:id/videos - Retrieve all videos for a specific author
app.get("/api/author/:id/videos", (req, res) => {
  const authorId = req.params.id;
  const cacheKey = `author_videos_${authorId}`;
  const cached = getCache(cacheKey);
  
  // Return cached data if available
  if (cached) {
    return res.json(cached);
  }

  // Query to get all videos for the specified author, ordered chronologically
  db.all(
    `SELECT id, original_name, original_url, original_thumbnail, date, repost_name, repost_url, repost_thumbnail, translation_status, comment 
     FROM videos 
     WHERE author = ? 
     ORDER BY date ASC, id ASC`,
    [authorId],
    (err, rows) => {
      if (err) return res.status(500).json({ error: err.message });
      setCache(cacheKey, rows);
      res.json(rows);
    },
  );
});

// Helper function to parse and validate search filters
function parseSearchFilters(query) {
  return {
    author: query.author ? parseInt(query.author) : 'all',
    dateFrom: query.dateFrom || null,
    dateTo: query.dateTo || null,
    translationStatus: query.translationStatus || 'all',
    limit: Math.min(parseInt(query.limit) || 100, 500)
  };
}

// Cache for search data to improve performance
let videosCache = null;
let authorsCache = null;
let cacheTimestamp = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Function to refresh search cache
function refreshSearchCache(callback) {
  const now = Date.now();
  if (videosCache && authorsCache && (now - cacheTimestamp) < CACHE_DURATION) {
    return callback(null);
  }
  
  // Load videos for search
  const videoQuery = `
    SELECT v.id, v.original_name, v.original_url, v.original_thumbnail, 
           v.date, v.repost_name, v.repost_url, v.repost_thumbnail, 
           v.translation_status, v.comment, v.author,
           a.id as author_id, a.yt_name, a.nico_name, a.twitter_name,
           a.yt_url, a.yt_avatar, a.nico_url, a.nico_avatar, 
           a.twitter_url, a.twitter_avatar
    FROM videos v
    JOIN authors a ON v.author = a.id
    ORDER BY v.id
  `;
  
  // Load authors for search
  const authorQuery = `
    SELECT a.id, a.yt_name, a.yt_url, a.yt_avatar, 
           a.nico_name, a.nico_url, a.nico_avatar,
           a.twitter_name, a.twitter_url, a.twitter_avatar,
           a.comment,
           COUNT(v.id) as worksCount,
           MAX(v.date) as lastUpdate
    FROM authors a
    LEFT JOIN videos v ON a.id = v.author
    GROUP BY a.id
    ORDER BY a.id
  `;
  
  let completed = 0;
  let error = null;
  
  db.all(videoQuery, [], (err, videoRows) => {
    if (err) error = err;
    else videosCache = videoRows;
    
    completed++;
    if (completed === 2) {
      if (error) return callback(error);
      cacheTimestamp = now;
      callback(null);
    }
  });
  
  db.all(authorQuery, [], (err, authorRows) => {
    if (err) error = err;
    else authorsCache = authorRows;
    
    completed++;
    if (completed === 2) {
      if (error) return callback(error);
      cacheTimestamp = now;
      callback(null);
    }
  });
}

// GET /api/search/videos - Search videos with fuzzy matching and filters
app.get("/api/search/videos", (req, res) => {
  const searchTerm = req.query.q;
  const filters = parseSearchFilters(req.query);
  
  if (!searchTerm) {
    return res.status(400).json({ error: "Search query cannot be empty" });
  }
  
  // Create cache key including all parameters
  const cacheKey = `search_videos_${searchTerm}_${JSON.stringify(filters)}`;
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }
  
  // Refresh cache if needed
  refreshSearchCache((err) => {
    if (err) {
      return res.status(500).json({ error: "Failed to refresh search cache: " + err.message });
    }
    
    // Apply database filters first
    let filteredVideos = videosCache;
    
    // Apply author filter
    if (filters.author !== 'all') {
      console.log('Filtering by author ID:', filters.author, 'type:', typeof filters.author);
      filteredVideos = filteredVideos.filter(v => v.author === filters.author);
      console.log('Videos after author filter:', filteredVideos.length);
    }
    
    // Apply date filters
    if (filters.dateFrom) {
      filteredVideos = filteredVideos.filter(v => v.date && v.date >= filters.dateFrom);
    }
    if (filters.dateTo) {
      filteredVideos = filteredVideos.filter(v => v.date && v.date <= filters.dateTo);
    }
    
    // Apply translation status filter
    if (filters.translationStatus !== 'all') {
      const status = parseInt(filters.translationStatus);
      filteredVideos = filteredVideos.filter(v => v.translation_status === status);
    }
    
    // Perform fuzzy search on filtered results
    const fuse = new Fuse(filteredVideos, VIDEO_SEARCH_OPTIONS);
    const searchResults = fuse.search(searchTerm);
    
    // Transform results and limit
    const results = searchResults
      .slice(0, filters.limit)
      .map(result => {
        const item = result.item;
        return {
          ...item,
          searchScore: result.score,
          matches: result.matches // Include match information for debugging
        };
      });
    
    // Add translation status text
    const finalResults = results.map(video => ({
      ...video,
      translation_status_text: TRANSLATION_STATUS[video.translation_status] || '未知',
      matches: undefined // Remove matches from final output
    }));
    
    setCache(cacheKey, finalResults);
    res.json(finalResults);
  });
});

// GET /api/search/authors - Search authors with fuzzy matching
app.get("/api/search/authors", (req, res) => {
  const searchTerm = req.query.q;
  const limit = Math.min(parseInt(req.query.limit) || 50, 200);
  
  if (!searchTerm) {
    return res.status(400).json({ error: "Search query cannot be empty" });
  }
  
  const cacheKey = `search_authors_${searchTerm}_${limit}`;
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }
  
  // Refresh cache if needed
  refreshSearchCache((err) => {
    if (err) {
      return res.status(500).json({ error: "Failed to refresh search cache: " + err.message });
    }
    
    // Perform fuzzy search on authors
    const fuse = new Fuse(authorsCache, AUTHOR_SEARCH_OPTIONS);
    const searchResults = fuse.search(searchTerm);
    
    // Transform and limit results
    const results = searchResults
      .slice(0, limit)
      .map(result => ({
        ...result.item,
        searchScore: result.score,
        displayName: result.item.yt_name || result.item.nico_name || result.item.twitter_name || 'Unknown'
      }));
    
    setCache(cacheKey, results);
    res.json(results);
  });
});

// GET /api/authors/list - Get simplified authors list for filters
app.get("/api/authors/list", (req, res) => {
  const cacheKey = 'authors_list';
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }
  
  // Query to get simplified author list for dropdowns
  const query = `
    SELECT 
      a.id, 
      COALESCE(a.yt_name, a.nico_name, a.twitter_name) as name,
      COUNT(v.id) as videoCount
    FROM authors a
    LEFT JOIN videos v ON a.id = v.author
    GROUP BY a.id
    HAVING videoCount > 0
    ORDER BY name ASC
  `;
  
  db.all(query, [], (err, rows) => {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    setCache(cacheKey, rows);
    res.json(rows);
  });
});

// GET /api/stats - Retrieve database statistics for dashboard display
app.get("/api/stats", (req, res) => {
  const cacheKey = 'stats';
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }

  // Query to calculate total authors, videos, and translated videos count
  db.all(
    `SELECT 
      COUNT(DISTINCT a.id) as totalAuthors,
      COUNT(v.id) as totalVideos,
      COUNT(CASE WHEN v.translation_status IN (1, 2) THEN 1 END) as translatedVideos
     FROM authors a
     LEFT JOIN videos v ON a.id = v.author`,
    [],
    (err, rows) => {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      setCache(cacheKey, rows[0]);
      res.json(rows[0]);
    }
  );
});

// Health check endpoint for monitoring and debugging
app.get("/health", (req, res) => {
  res.json({ 
    status: "ok", 
    timestamp: new Date().toISOString(),
    cacheSize: cache.size // Current number of cached items
  });
});

// Start the server on port 3000
app.listen(3000, () => {
  console.log("API server running on http://localhost:3000");
  console.log("Health check: http://localhost:3000/health");
});
