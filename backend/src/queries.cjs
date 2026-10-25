// Read-only queries. Aggregate counts before joining wide author records.
const AUTHORS = `
    WITH work_stats AS (
      SELECT author, COUNT(id) AS worksCount, MAX(date) AS lastUpdate
      FROM videos
      GROUP BY author
    ), original_duration_samples AS (
      SELECT
        author,
        CASE
          WHEN MAX(original_duration) IS NOT NULL THEN MAX(original_duration)
          ELSE MAX(repost_duration)
        END AS duration
      FROM videos
      WHERE original_url IS NOT NULL AND TRIM(original_url) != ''
      GROUP BY author, original_url
    ),
    unlinked_duration_samples AS (
      SELECT author, COALESCE(original_duration, repost_duration) AS duration
      FROM videos
      WHERE original_url IS NULL OR TRIM(original_url) = ''
    ),
    duration_stats AS (
      SELECT author, AVG(duration) AS averageDuration, COUNT(duration) AS durationKnownCount
      FROM (
        SELECT * FROM original_duration_samples
        UNION ALL
        SELECT * FROM unlinked_duration_samples
      )
      GROUP BY author
    )
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
      COALESCE(ws.worksCount, 0) as worksCount,
      ws.lastUpdate,
      ds.averageDuration,
      COALESCE(ds.durationKnownCount, 0) as durationKnownCount
    FROM authors a
    LEFT JOIN work_stats ws ON a.id = ws.author
    LEFT JOIN duration_stats ds ON a.id = ds.author
    ORDER BY COALESCE(a.yt_name, a.nico_name, a.twitter_name) ASC
  `;

const AUTHOR_VIDEOS = `SELECT id, original_name, original_url, original_thumbnail, original_duration, date, repost_name, repost_url, repost_thumbnail, repost_duration, translation_status, comment
     FROM videos
     WHERE author = ?
     ORDER BY date ASC, id ASC`;

const SEARCH_VIDEOS = `
    SELECT v.id, v.original_name, v.original_url, v.original_thumbnail,
           v.original_duration, v.date, v.repost_name, v.repost_url,
           v.repost_thumbnail, v.repost_duration,
           v.translation_status, v.comment, v.author,
           a.id as author_id, a.yt_name, a.nico_name, a.twitter_name,
           a.yt_url, a.yt_avatar, a.nico_url, a.nico_avatar,
           a.twitter_url, a.twitter_avatar
    FROM videos v
    JOIN authors a ON v.author = a.id
    ORDER BY v.id
  `;

const SEARCH_AUTHORS = `
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

const AUTHORS_LIST = `
    SELECT a.id,
           COALESCE(a.yt_name, a.nico_name, a.twitter_name) AS name,
           counts.videoCount
    FROM authors a
    JOIN (
      SELECT author, COUNT(id) AS videoCount
      FROM videos
      GROUP BY author
    ) counts ON counts.author = a.id
    ORDER BY name ASC
`;

const STATS = `
    SELECT (SELECT COUNT(*) FROM authors) AS totalAuthors,
           COUNT(v.id) AS totalVideos,
           COUNT(CASE WHEN v.translation_status IN (1, 2) THEN 1 END) AS translatedVideos,
           MAX(COALESCE(v.original_duration, v.repost_duration)) AS maxVideoDuration
    FROM videos v
    JOIN authors a ON a.id = v.author
`;

module.exports = {
  AUTHORS,
  AUTHOR_VIDEOS,
  SEARCH_VIDEOS,
  SEARCH_AUTHORS,
  AUTHORS_LIST,
  STATS,
};
