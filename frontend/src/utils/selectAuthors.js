import { getAuthorName } from "./authorDisplay.js";

export const selectAuthors = (items, filters, sortField, sortDirection) => {
  const f = filters;
  const durationFilterActive =
    f.minAverageDuration !== null || f.maxAverageDuration !== null;
  const filtered = items.filter((author) => {
    if (f.minWorks !== null && author.worksCount < f.minWorks) return false;
    if (f.maxWorks !== null && author.worksCount > f.maxWorks) return false;
    if (durationFilterActive) {
      if (
        author.averageDuration === null ||
        author.averageDuration === undefined
      ) {
        return f.includeUnknownDuration;
      }
      if (
        f.minAverageDuration !== null &&
        author.averageDuration < f.minAverageDuration
      )
        return false;
      if (
        f.maxAverageDuration !== null &&
        author.averageDuration > f.maxAverageDuration
      )
        return false;
    }
    return true;
  });
  const sorted = [...filtered].sort((a, b) => {
    let comparison = 0;

    switch (sortField) {
      case "name":
        // Use Japanese-friendly sorting, supporting kana and kanji
        const nameA = getAuthorName(a);
        const nameB = getAuthorName(b);
        comparison = nameA.localeCompare(nameB, ["ja-JP", "zh-CN", "en-US"], {
          sensitivity: "base",
          numeric: true,
          ignorePunctuation: true,
        });
        break;
      case "worksCount":
        comparison = a.worksCount - b.worksCount;
        break;
      case "lastUpdate":
        const dateA = a.lastUpdate ? new Date(a.lastUpdate) : new Date(0);
        const dateB = b.lastUpdate ? new Date(b.lastUpdate) : new Date(0);
        comparison = dateA - dateB;
        break;
      default:
        comparison = 0;
    }

    return sortDirection === "asc" ? comparison : -comparison;
  });

  return sorted;
};
