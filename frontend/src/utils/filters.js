export const defaultAuthorFilters = () => ({
  minWorks: null,
  maxWorks: null,
  minAverageDuration: null,
  maxAverageDuration: null,
  includeUnknownDuration: false,
});

export const defaultVideoFilters = () => ({
  minDuration: null,
  maxDuration: null,
  translationStatus: "all",
  dateFrom: "",
  dateTo: "",
  includeUnknownDuration: false,
});

export const parseNonNegative = (value) => {
  if (value === undefined || value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
};

export const queryValue = (query, shortKey, legacyKey) =>
  query[shortKey] ?? query[legacyKey];

export const authorFiltersFromQuery = (query) => ({
  minWorks: parseNonNegative(queryValue(query, "minW", "minWorks")),
  maxWorks: parseNonNegative(queryValue(query, "maxW", "maxWorks")),
  minAverageDuration: parseNonNegative(
    queryValue(query, "minDur", "minAvgDuration"),
  ),
  maxAverageDuration: parseNonNegative(
    queryValue(query, "maxDur", "maxAvgDuration"),
  ),
  includeUnknownDuration:
    queryValue(query, "unknown", "includeUnknownDuration") === "1",
});

export const videoFiltersFromQuery = (query) => ({
  minDuration: parseNonNegative(queryValue(query, "minDur", "minDuration")),
  maxDuration: parseNonNegative(queryValue(query, "maxDur", "maxDuration")),
  translationStatus: queryValue(query, "status", "translationStatus") || "all",
  dateFrom: queryValue(query, "from", "dateFrom") || "",
  dateTo: queryValue(query, "to", "dateTo") || "",
  includeUnknownDuration:
    queryValue(query, "unknown", "includeUnknownDuration") === "1",
});

export const translationOptions = [
  { title: "全部", value: "all" },
  { title: "中文内嵌", value: "1" },
  { title: "CC字幕", value: "2" },
  { title: "弹幕翻译", value: "3" },
  { title: "无需翻译", value: "4" },
  { title: "暂无翻译", value: "5" },
];
