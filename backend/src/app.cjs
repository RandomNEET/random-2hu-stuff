const express = require("express");
const cors = require("cors");
const { AsyncLruCache } = require("./cache.cjs");
const { createSearchService, parseSearchFilters } = require("./search.cjs");

function createApp({ repository, now = Date.now, cacheOptions = {} }) {
  const app = express();
  app.use(cors());
  const cache = new AsyncLruCache({ ...cacheOptions, now });
  const search = createSearchService(repository, { now });
  const cleanup = setInterval(() => cache.prune(), 60000);
  cleanup.unref();

  // Cache the wire payload so hot requests do not repeat JSON serialization.
  async function respond(res, key, loader, errorPrefix = "") {
    try {
      const json = await cache.load(key, async () =>
        JSON.stringify(await loader()),
      );
      res.type("json").send(json);
    } catch (error) {
      res.status(500).json({ error: errorPrefix + error.message });
    }
  }

  app.get("/api/authors", (req, res) =>
    respond(res, "authors", () => repository.authors()),
  );
  app.get("/api/author/:id/videos", (req, res) =>
    respond(res, `author_videos_${req.params.id}`, () =>
      repository.authorVideos(req.params.id),
    ),
  );
  app.get("/api/authors/list", (req, res) =>
    respond(res, "authors_list", () => repository.authorsList()),
  );
  app.get("/api/stats", (req, res) =>
    respond(res, "stats", () => repository.stats()),
  );

  app.get("/api/search/videos", (req, res) => {
    const term = req.query.q;
    if (!term)
      return res.status(400).json({ error: "Search query cannot be empty" });
    const filters = parseSearchFilters(req.query);
    return respond(
      res,
      `search_videos_${term}_${JSON.stringify(filters)}`,
      () => search.videos(term, filters),
      "Failed to refresh search cache: ",
    );
  });
  app.get("/api/search/authors", (req, res) => {
    const term = req.query.q;
    if (!term)
      return res.status(400).json({ error: "Search query cannot be empty" });
    const limit = Math.min(parseInt(req.query.limit) || 50, 200);
    return respond(
      res,
      `search_authors_${term}_${limit}`,
      () => search.authors(term, limit),
      "Failed to refresh search cache: ",
    );
  });
  app.get("/health", (req, res) =>
    res.json({
      status: "ok",
      timestamp: new Date(now()).toISOString(),
      cacheSize: cache.size,
    }),
  );

  return { app, close: () => clearInterval(cleanup) };
}

module.exports = { createApp };
