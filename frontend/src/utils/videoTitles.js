import { normalizeTextForSearch } from "./searchText.js";

const compareTitles = (titleA, titleB, normalizeTitle, locales, extraOptions = {}) => {
  if (
    titleA.length === titleB.length &&
    titleA.length > 0 &&
    titleB.length > 0
  ) {
    const getNumber = (title) => {
      const arabicMatch = title.match(/[1-9]/);
      if (arabicMatch) {
        return parseInt(arabicMatch[0]);
      }

      const chineseNumbers = {
        一: 1,
        二: 2,
        三: 3,
        四: 4,
        五: 5,
        六: 6,
        七: 7,
        八: 8,
        九: 9,
      };
      const chineseMatch = title.match(/[一二三四五六七八九]/);
      if (chineseMatch) {
        return chineseNumbers[chineseMatch[0]];
      }

      return null;
    };

    const calculateSimilarity = (str1, str2) => {
      const normalize = (str) =>
        normalizeTitle(str).replace(/[1-9一二三四五六七八九]/g, "").trim();
      const normalized1 = normalize(str1);
      const normalized2 = normalize(str2);

      if (normalized1 === normalized2) return 1.0;

      const getLevenshteinDistance = (a, b) => {
        if (a.length === 0) return b.length;
        if (b.length === 0) return a.length;

        const matrix = [];
        for (let i = 0; i <= b.length; i++) {
          matrix[i] = [i];
        }
        for (let j = 0; j <= a.length; j++) {
          matrix[0][j] = j;
        }

        for (let i = 1; i <= b.length; i++) {
          for (let j = 1; j <= a.length; j++) {
            if (b.charAt(i - 1) === a.charAt(j - 1)) {
              matrix[i][j] = matrix[i - 1][j - 1];
            } else {
              matrix[i][j] = Math.min(
                matrix[i - 1][j - 1] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j] + 1,
              );
            }
          }
        }

        return matrix[b.length][a.length];
      };

      const distance = getLevenshteinDistance(normalized1, normalized2);
      const maxLength = Math.max(normalized1.length, normalized2.length);
      return maxLength === 0 ? 1.0 : 1.0 - distance / maxLength;
    };

    const numberA = getNumber(titleA);
    const numberB = getNumber(titleB);

    if (numberA !== null && numberB !== null) {
      const similarity = calculateSimilarity(titleA, titleB);
      if (similarity >= 0.8) {
        return numberA - numberB;
      }
    }
  }

  return titleA.localeCompare(titleB, locales, {
    numeric: true,
    ignorePunctuation: true,
    sensitivity: "base",
    ...extraOptions,
  });
};

// These pages historically use different normalization and locale priorities.
export const compareAuthorVideoTitles = (a, b) => compareTitles(a, b, text => text, ["ja-JP", "en-US"]);
export const compareSearchVideoTitles = (a, b) => compareTitles(a, b, normalizeTextForSearch, ["zh-CN", "ja-JP", "en-US"], { usage: "sort" });
