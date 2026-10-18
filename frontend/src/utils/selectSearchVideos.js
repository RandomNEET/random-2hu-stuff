import { compareSearchVideoTitles as compareVideoTitles } from "./videoTitles.js";

export const selectSearchVideos = (items, sortField, sortDirection) => {
  const sorted = [...items].sort((a, b) => {
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

      if (!dateA && !dateB) {
        const titleA = a.original_name || "";
        const titleB = b.original_name || "";
        return compareVideoTitles(titleA, titleB);
      }
      if (!dateA) return 1;
      if (!dateB) return -1;

      const dateComparison = dateA - dateB;
      if (dateComparison !== 0) {
        return dateComparison;
      }

      const titleA = a.original_name || "";
      const titleB = b.original_name || "";
      return compareVideoTitles(titleA, titleB);
    } else if (sortField === "relevance") {
      const indexA = items.findIndex(
        (v) => v.id === a.id,
      );
      const indexB = items.findIndex(
        (v) => v.id === b.id,
      );

      const comparison = indexA - indexB;
      return sortDirection === "asc" ? comparison : -comparison;
    }

    return 0;
  });

  return sorted;
};
