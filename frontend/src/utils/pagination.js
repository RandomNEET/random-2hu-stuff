export const paginationItems = (currentPage, totalPages, windowWidth) => {
  const current = currentPage;
  const total = totalPages;
  const items = [];

  // Decide display strategy based on screen size
  const isMobileView = windowWidth <= 768;
  const maxDisplayPages = isMobileView ? 5 : 9;
  const ellipsisThreshold = isMobileView ? 3 : 5;

  // If total pages <= max display pages, show all page numbers
  if (total <= maxDisplayPages) {
    for (let i = 1; i <= total; i++) {
      items.push({ type: "page", page: i });
    }
    return items;
  }

  // Case when total pages > max display pages
  const showLeftEllipsis = current >= ellipsisThreshold;
  const showRightEllipsis = current <= total - (ellipsisThreshold - 1);

  if (isMobileView) {
    // Mobile logic: maximum 5 elements (including ellipsis)
    if (showLeftEllipsis && showRightEllipsis) {
      // Both sides have ellipsis: 1 ... current ... total (5 elements)
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: Math.max(1, current - 1) });
      items.push({ type: "page", page: current });
      items.push({
        type: "ellipsis",
        targetPage: Math.min(total, current + 1),
      });
      items.push({ type: "page", page: total });
    } else if (showLeftEllipsis) {
      // Only left ellipsis: 1 ... current-1 current total (5 elements)
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: Math.max(1, current - 1) });
      if (current > total - 1) {
        items.push({ type: "page", page: total - 1 });
      } else {
        items.push({ type: "page", page: current - 1 });
      }
      items.push({ type: "page", page: current });
      items.push({ type: "page", page: total });
    } else if (showRightEllipsis) {
      // Only right ellipsis: 1 current current+1 ... total (5 elements)
      items.push({ type: "page", page: 1 });
      if (current === 1) {
        items.push({ type: "page", page: 2 });
        items.push({ type: "page", page: 3 });
      } else {
        items.push({ type: "page", page: current });
        items.push({ type: "page", page: current + 1 });
      }
      items.push({
        type: "ellipsis",
        targetPage: Math.min(total, current + 2),
      });
      items.push({ type: "page", page: total });
    } else {
      // No ellipsis: show all page numbers
      for (let i = 1; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    }
  } else {
    // Desktop logic: maintain original 9-page logic
    if (showLeftEllipsis && showRightEllipsis) {
      // Both sides have ellipsis: 1 ... current-2 current-1 current current+1 current+2 ... total
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: current - 3 });
      for (let i = current - 2; i <= current + 2; i++) {
        items.push({ type: "page", page: i });
      }
      items.push({ type: "ellipsis", targetPage: current + 3 });
      items.push({ type: "page", page: total });
    } else if (showLeftEllipsis) {
      // Only left ellipsis: 1 ... current-2 current-1 current current+1 current+2 ... total
      items.push({ type: "page", page: 1 });
      items.push({ type: "ellipsis", targetPage: current - 3 });
      for (let i = current - 2; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    } else if (showRightEllipsis) {
      // Only right ellipsis: 1 2 3 4 5 current current+1 current+2 ... total
      for (let i = 1; i <= current + 2; i++) {
        items.push({ type: "page", page: i });
      }
      items.push({ type: "ellipsis", targetPage: current + 3 });
      items.push({ type: "page", page: total });
    } else {
      // No ellipsis: show all page numbers (this case is handled when total <= 9)
      for (let i = 1; i <= total; i++) {
        items.push({ type: "page", page: i });
      }
    }
  }

  return items;
};
