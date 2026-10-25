export const normalizeTextForSearch = (text) => {
  if (!text) return "";

  let normalized = text.toLowerCase().normalize("NFD");

  normalized = normalized.replace(/[・･｜·]/g, " ");
  normalized = normalized.replace(/[「」『』【】〔〕〈〉《》（）()]/g, "");
  normalized = normalized.replace(/[！？｡､。，、]/g, "");
  normalized = normalized.replace(/[~～]/g, "");
  normalized = normalized.replace(/['"'""`]/g, "");
  normalized = normalized.replace(/[＃#％%]/g, "");
  normalized = normalized.replace(/[　\s]+/g, " ").trim();

  return normalized;
};

export const isTextMatch = (text, query) => {
  if (!text || !query) return false;

  const normalizedText = normalizeTextForSearch(text);
  const normalizedQuery = normalizeTextForSearch(query);

  if (normalizedText.includes(normalizedQuery)) return true;

  if (query.length <= 2) {
    return normalizedText.includes(normalizedQuery);
  }

  const getTextSegments = (text) => {
    const segments = [];
    segments.push(...text.split(/\s+/).filter((seg) => seg.length > 0));

    const scriptBoundaryPattern = /([ひ-ゟ]+|[ア-ヿ]+|[一-龯]+|[a-z0-9]+)/g;
    const scriptSegments = text.match(scriptBoundaryPattern) || [];
    segments.push(...scriptSegments);

    return [...new Set(segments)].filter((seg) => seg.length > 0);
  };

  const querySegments = getTextSegments(normalizedQuery);
  const textSegments = getTextSegments(normalizedText);

  if (querySegments.length > 1) {
    const foundSegments = querySegments.filter((querySegment) => {
      const isCJK = /[一-龯ひ-ゟア-ヿ]/.test(querySegment);
      const minLength = isCJK ? 1 : 2;

      if (querySegment.length < minLength) return false;

      return textSegments.some(
        (textSegment) =>
          textSegment.includes(querySegment) ||
          querySegment.includes(textSegment),
      );
    });

    const matchRatio = foundSegments.length / querySegments.length;
    return matchRatio >= 0.6;
  }

  if (querySegments.length === 1) {
    const querySegment = querySegments[0];
    const isCJK = /[一-龯ひ-ゟア-ヿ]/.test(querySegment);

    if (isCJK && querySegment.length === 1) {
      return textSegments.some((seg) => seg.includes(querySegment));
    } else if (querySegment.length >= 2) {
      return textSegments.some(
        (seg) =>
          seg.includes(querySegment) ||
          querySegment.includes(seg) ||
          (seg.length >= 2 &&
            querySegment.length >= 2 &&
            (seg.includes(
              querySegment.substring(0, Math.min(3, querySegment.length)),
            ) ||
              querySegment.includes(
                seg.substring(0, Math.min(3, seg.length)),
              ))),
      );
    }
  }

  return false;
};

// Link queries are matched by the backend, including platform URL aliases.
export const isLinkSearch = (query) =>
  /^(?:https?:\/\/|\/\/|[\w.-]+\.[a-z]{2,}\/)/i.test(query.trim());
