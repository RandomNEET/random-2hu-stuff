/** Serialize header searches; parameter aliases remain unchanged. */
export const buildSearchQuery = (form, findAuthorIdByName) => {
  const query = {
    q: form.query.trim(),
    type: form.type,
    limit: form.limit,
  };

  // Add video-specific filters
  if (form.type === "videos") {
    // Handle author input - convert author name to ID
    if (form.filters.authorInput) {
      const authorId = findAuthorIdByName(form.filters.authorInput);
      if (authorId) {
        query.author = authorId;
      }
    }
    if (form.filters.translationStatus !== "all") {
      query.status = form.filters.translationStatus;
    }
    if (form.filters.dateFrom) {
      query.from = form.filters.dateFrom;
    }
    if (form.filters.dateTo) {
      query.to = form.filters.dateTo;
    }
    if (form.filters.minDuration !== null) {
      query.minDur = form.filters.minDuration;
    }
    if (form.filters.maxDuration !== null) {
      query.maxDur = form.filters.maxDuration;
    }
    if (
      (form.filters.minDuration !== null ||
        form.filters.maxDuration !== null) &&
      form.filters.includeUnknownDuration
    ) {
      query.unknown = "1";
    }
  }

  return query;
};

// API parameter names differ from the public short URL aliases.
export const buildSearchParams = (query, routeQuery) => {
  const value = (shortKey, legacyKey) =>
    routeQuery[shortKey] ?? routeQuery[legacyKey];
  const status = value("status", "translationStatus");
  const dateFrom = value("from", "dateFrom");
  const dateTo = value("to", "dateTo");
  const minDuration = value("minDur", "minDuration");
  const maxDuration = value("maxDur", "maxDuration");
  const includeUnknownDuration =
    value("unknown", "includeUnknownDuration") === "1";
  return new URLSearchParams({
    q: query,
    limit: routeQuery.limit || "100",
    ...(routeQuery.type && { type: routeQuery.type }),
    ...(routeQuery.author && { author: routeQuery.author }),
    ...(status && status !== "all" && { translationStatus: status }),
    ...(dateFrom && { dateFrom }),
    ...(dateTo && { dateTo }),
    ...(minDuration && { minDuration }),
    ...(maxDuration && { maxDuration }),
    ...(includeUnknownDuration && { includeUnknownDuration: "1" }),
  });
};
