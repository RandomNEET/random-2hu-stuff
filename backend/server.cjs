const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const cors = require("cors");

const app = express();
app.use(cors());

// 优化SQLite配置
const db = new sqlite3.Database("./random-2hu-stuff.db", (err) => {
  if (err) {
    console.error('Error opening database:', err);
  } else {
    console.log('Connected to SQLite database');
    // 优化SQLite性能
    db.run("PRAGMA journal_mode=WAL");
    db.run("PRAGMA synchronous=NORMAL");
    db.run("PRAGMA cache_size=10000");
    db.run("PRAGMA temp_store=MEMORY");
  }
});

// 简单的内存缓存
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5分钟缓存

function setCache(key, data) {
  cache.set(key, {
    data,
    timestamp: Date.now()
  });
}

function getCache(key) {
  const item = cache.get(key);
  if (item && (Date.now() - item.timestamp) < CACHE_TTL) {
    return item.data;
  }
  cache.delete(key);
  return null;
}

// 清理过期缓存
setInterval(() => {
  const now = Date.now();
  for (const [key, item] of cache.entries()) {
    if (now - item.timestamp > CACHE_TTL) {
      cache.delete(key);
    }
  }
}, 60000); // 每分钟清理一次

app.get("/api/authors", (req, res) => {
  const cacheKey = 'authors';
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }

  const query = `
    SELECT 
      a.id, 
      a.name, 
      a.url, 
      a.avatar,
      COUNT(v.id) as worksCount,
      MAX(v.date) as lastUpdate
    FROM authors a
    LEFT JOIN videos v ON a.id = v.author
    GROUP BY a.id, a.name, a.url, a.avatar
    ORDER BY a.name ASC
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

app.get("/api/author/:id/videos", (req, res) => {
  const authorId = req.params.id;
  const cacheKey = `author_videos_${authorId}`;
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }

  db.all(
    `SELECT id, original_name, original_url, date, repost_name, repost_url, translation_status 
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

app.get("/api/search/videos", (req, res) => {
  const query = req.query.q;
  if (!query) {
    return res.status(400).json({ error: "搜索关键词不能为空" });
  }
  
  // 限制搜索结果数量
  const limit = Math.min(parseInt(req.query.limit) || 100, 500);
  const cacheKey = `search_${query}_${limit}`;
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }
  
  db.all(
    `SELECT v.id, v.original_name, v.original_url, v.date, v.repost_name, v.repost_url, v.translation_status,
            a.id as author_id, a.name as author_name, a.avatar as author_avatar
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

app.get("/api/stats", (req, res) => {
  const cacheKey = 'stats';
  const cached = getCache(cacheKey);
  
  if (cached) {
    return res.json(cached);
  }

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

// 健康检查端点
app.get("/health", (req, res) => {
  res.json({ 
    status: "ok", 
    timestamp: new Date().toISOString(),
    cacheSize: cache.size 
  });
});

app.listen(3000, () => {
  console.log("API server running on http://localhost:3000");
  console.log("Health check: http://localhost:3000/health");
});
