const sqlite3 = require("../../../backend/node_modules/sqlite3");

function execute(db, sql) {
  return new Promise((resolve, reject) => db.exec(sql, (error) => error ? reject(error) : resolve()));
}
function all(db, sql, params = []) {
  return new Promise((resolve, reject) => db.all(sql, params, (error, rows) => error ? reject(error) : resolve(rows)));
}
function close(db) {
  return new Promise((resolve, reject) => db.close((error) => error ? reject(error) : resolve()));
}
async function fixtureDatabase(filename = ":memory:", { authors = 6, videos = 90 } = {}) {
  const db = await new Promise((resolve, reject) => {
    const connection = new sqlite3.Database(filename, (error) => error ? reject(error) : resolve(connection));
  });
  await execute(db, `
    CREATE TABLE authors (
      id INTEGER PRIMARY KEY, yt_name TEXT, yt_url TEXT, yt_avatar TEXT,
      nico_name TEXT, nico_url TEXT, nico_avatar TEXT,
      twitter_name TEXT, twitter_url TEXT, twitter_avatar TEXT, comment TEXT
    );
    CREATE TABLE videos (
      id INTEGER PRIMARY KEY, author INTEGER, original_name TEXT, original_url TEXT,
      original_thumbnail TEXT, original_duration INTEGER, date TEXT, repost_name TEXT,
      repost_url TEXT, repost_thumbnail TEXT, repost_duration INTEGER,
      translation_status INTEGER, comment TEXT
    );
  `);
  const statements = [];
  for (let id = 1; id <= authors; id++) {
    // Include equal names, empty names, missing platform names and an author with no works.
    const name = id % 5 === 0 ? "NULL" : `'作者 ${id % 4}'`;
    statements.push(`INSERT INTO authors VALUES (${id}, ${name}, 'https://youtube.com/@${id}', NULL,
      'ニコ ${id}', NULL, NULL, NULL, NULL, NULL, '作者备注');`);
  }
  for (let id = 1; id <= videos; id++) {
    const author = id % Math.max(1, authors - 1) + 1;
    const original = id % 8 === 0 ? "NULL" : id % 9 === 0 ? "'  '" : `'original-${Math.floor(id / 3)}'`;
    const duration = id % 4 === 0 ? "NULL" : id % 7 === 0 ? 0 : id * 5;
    const repostDuration = id % 6 === 0 ? "NULL" : id % 4 === 0 ? 70 : 30;
    const date = id % 10 === 0 ? "NULL" : `'2026-10-${String(id % 20 + 1).padStart(2, "0")}'`;
    const status = id % 6 === 0 ? "NULL" : id % 6;
    statements.push(`INSERT INTO videos VALUES (${id}, ${author}, '东方 第${id}话', ${original},
      NULL, ${duration}, ${date}, '字幕 ${id}', 'repost-${id}', NULL, ${repostDuration}, ${status}, '動画 test');`);
  }
  // Orphan rows must remain excluded from joined search data and global video statistics.
  statements.push(`INSERT INTO videos (id, author, original_name, original_duration, translation_status)
    VALUES (${videos + 1}, 999999, 'orphan', 999999, 1);`);
  statements.push(`INSERT INTO videos (id, author, original_name, original_url, original_duration, repost_duration, translation_status)
    VALUES (${videos + 2}, 1, '东方 shared', 'same-original', 60, 900, 1),
           (${videos + 3}, 1, '东方 shared', 'same-original', 120, 800, 2),
           (${videos + 4}, 1, '东方 shared', 'same-original', NULL, 1000, 3),
           (${videos + 5}, 1, '东方 unlinked', '', 0, 500, NULL);`);
  await execute(db, "BEGIN;\n" + statements.join("\n") + "\nCOMMIT;");
  return db;
}

module.exports = { fixtureDatabase, execute, all, close };
