const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { createApp } = require("../../backend/src/app.cjs");
const { openDatabase, createRepository } = require("../../backend/src/database.cjs");
const { fixtureDatabase, execute, all, close } = require("./fixtures/database.cjs");
const { legacyApi } = require("./fixtures/legacy.cjs");

async function serve(t, repository, options = {}) {
  const service = createApp({ repository, ...options });
  const server = await new Promise((resolve, reject) => {
    const instance = service.app.listen(0, "127.0.0.1", () => resolve(instance));
    instance.once("error", reject);
  }).catch(error => { service.close(); throw error; });
  t.after(async () => {
    await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    service.close();
  });
  const base = `http://127.0.0.1:${server.address().port}`;
  return { base, request: async target => {
    const response = await fetch(base + target);
    return { status: response.status, body: await response.json() };
  } };
}

test("public responses and search ordering/scores match the pre-refactor server", async t => {
  const db = await fixtureDatabase();
  t.after(() => close(db));
  const old = legacyApi(db);
  const api = await serve(t, createRepository(db));
  const targets = [
    "/api/authors", "/api/authors/list", "/api/stats",
    "/api/author/1/videos", "/api/author/6/videos", "/api/author/missing/videos",
    "/api/search/videos", "/api/search/authors", "/api/search/videos?q=",
    "/api/search/videos?q=东方", "/api/search/videos?q=動画", "/api/search/videos?q=notfound",
    "/api/search/videos?q=东方&author=2", "/api/search/videos?q=东方&author=invalid",
    "/api/search/videos?q=东方&dateFrom=2026-10-05&dateTo=2026-10-10",
    "/api/search/videos?q=东方&translationStatus=2", "/api/search/videos?q=东方&translationStatus=bad",
    "/api/search/videos?q=东方&minDuration=0&maxDuration=80",
    "/api/search/videos?q=东方&minDuration=60&includeUnknownDuration=1",
    "/api/search/videos?q=东方&minDuration=bad&maxDuration=-1",
    "/api/search/videos?q=东方&author=2&translationStatus=1&maxDuration=150",
    "/api/search/videos?q=东方&limit=2", "/api/search/videos?q=东方&limit=0",
    "/api/search/videos?q=东方&limit=-2", "/api/search/videos?q=东方&limit=9999",
    "/api/search/authors?q=作者", "/api/search/authors?q=ニコ&limit=2",
    "/api/search/authors?q=作者&limit=-1", "/api/search/authors?q=作者&limit=9999",
  ];
  for (const target of targets) {
    assert.deepEqual(await api.request(target), await old.request(target), target);
    // Hot responses must have the same wire representation and field presence, too.
    assert.deepEqual(await api.request(target), await old.request(target), `cached ${target}`);
  }
  const response = await fetch(api.base + "/api/authors");
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
  assert.match(response.headers.get("content-type"), /application\/json; charset=utf-8/);
  const conditional = await fetch(api.base + "/api/authors", {
    cache: "no-cache",
    headers: {"If-None-Match": response.headers.get("etag")},
  });
  assert.equal(conditional.status, 304);
  assert.equal((await fetch(api.base + "/api/videos")).status, 404);
});

test("aggregate queries preserve empty-database and orphan-row statistics", async t => {
  const db = await fixtureDatabase();
  t.after(() => close(db));
  await execute(db, "DELETE FROM authors; DELETE FROM videos;");
  const old = legacyApi(db);
  const api = await serve(t, createRepository(db));
  for (const target of ["/api/authors", "/api/authors/list", "/api/stats"]) {
    assert.deepEqual(await api.request(target), await old.request(target));
  }
});

test("database failures retain HTTP errors and successful retries work", async t => {
  const db = await fixtureDatabase();
  t.after(() => close(db));
  const repository = createRepository(db);
  let fail = true;
  const wrapped = Object.fromEntries(Object.entries(repository).map(([name, load]) => [name, (...args) => {
    if (fail) return Promise.reject(new Error("test database failure"));
    return load(...args);
  }]));
  const api = await serve(t, wrapped);
  assert.deepEqual(await api.request("/api/authors"), {status: 500, body: {error: "test database failure"}});
  assert.deepEqual(await api.request("/api/search/videos?q=东方"), {status: 500, body: {error: "Failed to refresh search cache: test database failure"}});
  fail = false;
  assert.equal((await api.request("/api/authors")).status, 200);
  assert.ok((await api.request("/api/search/videos?q=东方")).body.length > 0);
});

test("concurrent cold HTTP requests coalesce queries and respect the existing TTL", async t => {
  const db = await fixtureDatabase();
  t.after(() => close(db));
  const repository = createRepository(db);
  let now = 0, reads = 0;
  const wrapped = {...repository, authors: async () => {
    reads++;
    await new Promise(resolve => setTimeout(resolve, 15));
    return repository.authors();
  }};
  const api = await serve(t, wrapped, {now: () => now});
  await Promise.all(Array.from({length: 20}, () => api.request("/api/authors")));
  assert.equal(reads, 1);
  now = 300000;
  await api.request("/api/authors");
  assert.equal(reads, 2);
});

test("production database opener is read-only and never creates missing databases", async t => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "r2s-backend-"));
  t.after(() => fs.rm(dir, {recursive: true, force: true}));
  const filename = path.join(dir, "fixture.db");
  const writable = await fixtureDatabase(filename);
  await close(writable);
  const before = await fs.readFile(filename);
  const db = await openDatabase(filename);
  assert.ok((await all(db, "SELECT COUNT(*) AS n FROM authors"))[0].n > 0);
  await assert.rejects(execute(db, "DELETE FROM authors"), /readonly/i);
  await close(db);
  assert.deepEqual(await fs.readFile(filename), before);
  await assert.rejects(openDatabase(path.join(dir, "missing.db")), /CANTOPEN/);
  await assert.rejects(fs.access(path.join(dir, "missing.db")));
});

test("hot response payloads are serialized once and health retains its fields", async t => {
  let serializations = 0;
  const authors = [{toJSON() { serializations++; return {id: 1, yt_name: "作者"}; }}];
  const api = await serve(t, {authors: async () => authors});
  for (let i = 0; i < 5; i++) {
    assert.deepEqual((await api.request("/api/authors")).body, [{id: 1, yt_name: "作者"}]);
  }
  assert.equal(serializations, 1);
  const health = await api.request("/health");
  assert.equal(health.status, 200);
  assert.equal(health.body.status, "ok");
  assert.equal(health.body.cacheSize, 1);
  assert.ok(Number.isFinite(Date.parse(health.body.timestamp)));
});
