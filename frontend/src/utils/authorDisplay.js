// Keep each caller's null/empty fallback; these helpers express platform priority only.
export const getAuthorName = author => author.yt_name || author.nico_name || author.twitter_name || "Unknown";
export const getAuthorAvatar = author => author.nico_avatar || author.yt_avatar || author.twitter_avatar;
