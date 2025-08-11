const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const cors = require("cors");

const app = express();
app.use(cors());

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
      COUNT(v.id) as worksCount,
      MAX(v.date) as lastUpdate
    FROM authors a
    LEFT JOIN videos v ON a.id = v.author
    GROUP BY a.id, a.yt_name, a.yt_url, a.yt_avatar, a.nico_name, a.nico_url, a.nico_avatar
    ORDER BY COALESCE(a.yt_name, a.nico_name) ASC
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

// GET /api/search/videos - Search videos by title with fuzzy matching
app.get("/api/search/videos", (req, res) => {
  const query = req.query.q;
  if (!query) {
    return res.status(400).json({ error: "Search query cannot be empty" });
  }
  
  // Limit search results to prevent excessive memory usage and improve performance
  const limit = Math.min(parseInt(req.query.limit) || 100, 500);
  const cacheKey = `search_${query}_${limit}`;
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }
  
  // Search in both original and repost video names with author information
  db.all(
    `SELECT v.id, v.original_name, v.original_url, v.original_thumbnail, v.date, v.repost_name, v.repost_url, v.repost_thumbnail, v.translation_status, v.comment,
            a.id as author_id, a.yt_name, a.yt_url, a.yt_avatar, a.nico_name, a.nico_url, a.nico_avatar
     FROM videos v
     JOIN authors a ON v.author = a.id
     WHERE v.original_name LIKE ? OR v.repost_name LIKE ?
     ORDER BY v.date DESC, v.id DESC
     LIMIT ?`,
    [`%${query}%`, `%${query}%`, limit],
    (err, rows) => {
      if (err) return res.status(500).json({ error: err.message });
      setCache(cacheKey, rows);
      res.json(rows);
    }
  );
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
