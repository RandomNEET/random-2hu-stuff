import { compareAuthorVideoTitles as compareVideoTitles } from "./videoTitles.js";
const resolvedDuration = video => video.original_duration ?? video.repost_duration;

export const selectAuthorVideos = (items, filters, sortField, sortDirection) => {
  const f = filters;
  const durationFilterActive = f.minDuration !== null || f.maxDuration !== null;
  const filtered = items.filter((video) => {
    const duration = resolvedDuration(video);
    if (durationFilterActive) {
      if (duration === null || duration === undefined) {
        if (!f.includeUnknownDuration) return false;
      } else {
        if (f.minDuration !== null && duration < f.minDuration) return false;
        if (f.maxDuration !== null && duration > f.maxDuration) return false;
      }
    }
    if (
      f.translationStatus !== "all" &&
      String(video.translation_status) !== String(f.translationStatus)
    )
      return false;
    if (f.dateFrom && (!video.date || video.date < f.dateFrom)) return false;
    if (f.dateTo && (!video.date || video.date > f.dateTo)) return false;
    return true;
  });
  const sorted = [...filtered].sort((a, b) => {
    if (sortField === "date") {
      const dateA = a.date ? new Date(a.date) : null;
      const dateB = b.date ? new Date(b.date) : null;

      if (!dateA && !dateB) {
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      if (!dateA) return 1;
      if (!dateB) return -1;

      const comparison = dateA - dateB;
      if (comparison === 0) {
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      return sortDirection === "asc" ? comparison : -comparison;
    } else if (sortField === "translation") {
      const getTranslationPriority = (status) => {
        if (status === null || status === undefined || status === "") return 4;
        if (status === 1 || status === 2 || status === 4) return 1;
        if (status === 3) return 2;
        if (status === 5) return 3;
        return 4;
      };

      const priorityA = getTranslationPriority(a.translation_status);
      const priorityB = getTranslationPriority(b.translation_status);

      if (priorityA !== priorityB) {
        const priorityComparison = priorityA - priorityB;
        return sortDirection === "asc"
          ? priorityComparison
          : -priorityComparison;
      }

      const dateA = a.date ? new Date(a.date) : null;
      const dateB = b.date ? new Date(b.date) : null;

      if (!dateA && !dateB) return 0;
      if (!dateA) return 1;
      if (!dateB) return -1;

      return dateA - dateB;
    }

    return 0;
  });

  return sorted;
};
