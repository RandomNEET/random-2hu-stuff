const path = require("node:path");
const { openDatabase, createRepository } = require("./src/database.cjs");
const { createApp } = require("./src/app.cjs");

async function start() {
  const filename =
    process.env.DATABASE_PATH || path.join(__dirname, "random-2hu-stuff.db");
  const db = await openDatabase(filename);
  const service = createApp({ repository: createRepository(db) });
  const port = Number(process.env.PORT || 3000);
  const server = service.app.listen(port, () => {
    console.log(`API server running on http://localhost:${port}`);
    console.log(`Health check: http://localhost:${port}/health`);
  });
  const shutdown = () => {
    service.close();
    server.close(() => db.close());
  };
  process.once("SIGTERM", shutdown);
  process.once("SIGINT", shutdown);
  server.once("error", (error) => {
    service.close();
    db.close();
    console.error("API server failed:", error.message);
    process.exitCode = 1;
  });
  return { server, db, close: shutdown };
}

if (require.main === module) {
  start().catch((error) => {
    console.error("API server failed:", error.message);
    process.exitCode = 1;
  });
}

module.exports = { start };
