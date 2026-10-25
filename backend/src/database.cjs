const sqlite3 = require("sqlite3");
const queries = require("./queries.cjs");

// No migrations, persistent PRAGMAs, indexes or write access in the API process.
function openDatabase(filename) {
  return new Promise((resolve, reject) => {
    const db = new sqlite3.Database(
      filename,
      sqlite3.OPEN_READONLY,
      (error) => {
        if (error) reject(error);
        else {
          // These settings affect this connection's memory only, not the database file.
          db.exec(
            "PRAGMA cache_size=10000; PRAGMA temp_store=MEMORY;",
            (error) => {
              if (error) db.close(() => reject(error));
              else resolve(db);
            },
          );
        }
      },
    );
  });
}

function createRepository(db) {
  const all = (sql, params = []) =>
    new Promise((resolve, reject) => {
      db.all(sql, params, (error, rows) =>
        error ? reject(error) : resolve(rows),
      );
    });
  return {
    authors: () => all(queries.AUTHORS),
    authorVideos: (id) => all(queries.AUTHOR_VIDEOS, [id]),
    searchVideos: () => all(queries.SEARCH_VIDEOS),
    searchAuthors: () => all(queries.SEARCH_AUTHORS),
    authorsList: () => all(queries.AUTHORS_LIST),
    stats: async () => (await all(queries.STATS))[0],
  };
}

module.exports = { openDatabase, createRepository };
