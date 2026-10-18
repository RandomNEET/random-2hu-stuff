const VIDEO_SEARCH_OPTIONS = {
  keys: [
    { name: "original_name", weight: 0.7 },
    { name: "repost_name", weight: 0.9 },
    { name: "comment", weight: 0.3 },
  ],
  threshold: 0.4, // Lower = more strict matching
  distance: 100,
  includeScore: true,
  includeMatches: false,
  minMatchCharLength: 2,
  shouldSort: true,
  findAllMatches: false,
  ignoreLocation: true,
  ignoreFieldNorm: false,
};

const AUTHOR_SEARCH_OPTIONS = {
  keys: [
    { name: "yt_name", weight: 0.8 },
    { name: "nico_name", weight: 0.8 },
    { name: "twitter_name", weight: 0.8 },
  ],
  threshold: 0.3, // More strict for author names
  distance: 50,
  includeScore: true,
  includeMatches: false,
  minMatchCharLength: 1,
  shouldSort: true,
  findAllMatches: false,
  ignoreLocation: true,
};

const TRANSLATION_STATUS = {
  1: "中文内嵌",
  2: "CC字幕",
  3: "弹幕翻译",
  4: "无需翻译",
  5: "暂无翻译",
};

module.exports = { VIDEO_SEARCH_OPTIONS, AUTHOR_SEARCH_OPTIONS, TRANSLATION_STATUS };
