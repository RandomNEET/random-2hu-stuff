const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { parse } = require("node:querystring");
const Fuse = require("../../../backend/node_modules/fuse.js");

function legacyApi(db, { now = Date.now, FuseClass = Fuse } = {}) {
  const routes = new Map();
  const queries = [];
  const app = { use() {}, get(route, handler) { routes.set(route, handler); }, listen() {} };
  const connection = {
    all(sql, params, callback) {
      queries.push({ sql, params });
      db.all(sql, params, callback);
    },
    // Never apply the old server's persistent PRAGMAs, even to a test database.
    run() {},
  };
  class TestDate extends Date { static now() { return now(); } }
  const sandbox = {
    require(name) {
      if (name === "express") return () => app;
      if (name === "cors") return () => () => {};
      if (name === "fuse.js") return FuseClass;
      if (name === "sqlite3") return { verbose: () => ({
        Database: function (filename, callback) {
          queueMicrotask(() => callback(null));
          return connection;
        },
      }) };
      throw new Error(`Unexpected legacy dependency: ${name}`);
    },
    console: { log() {}, error() {} },
    setInterval() {},
    Date: TestDate,
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "legacy-server.cjs"), "utf8"), sandbox);
  async function request(target) {
    const url = new URL(target, "http://test.invalid");
    const authorMatch = url.pathname.match(/^\/api\/author\/(.+)\/videos$/);
    const route = authorMatch ? "/api/author/:id/videos" : url.pathname;
    return new Promise((resolve, reject) => {
      let status = 200;
      const req = { query: parse(url.search.slice(1)), params: authorMatch ? { id: decodeURIComponent(authorMatch[1]) } : {} };
      const res = {
        status(code) { status = code; return res; },
        json(body) { resolve({ status, body: JSON.parse(JSON.stringify(body)) }); },
      };
      try { routes.get(route)(req, res); } catch (error) { reject(error); }
    });
  }
  return { request, queries };
}
module.exports = { legacyApi };
