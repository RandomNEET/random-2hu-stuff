import { describe, expect, it } from "vitest";
import * as legacy from "../fixtures/legacy-logic.js";
import { authors, videos } from "../fixtures/api.js";
import { groupVideosByName } from "../../../frontend/src/utils/videoGroups.js";
import {
  compareAuthorVideoTitles,
  compareSearchVideoTitles,
} from "../../../frontend/src/utils/videoTitles.js";
import {
  normalizeTextForSearch,
  isTextMatch,
} from "../../../frontend/src/utils/searchText.js";
import { paginationItems } from "../../../frontend/src/utils/pagination.js";
import {
  defaultAuthorFilters,
  defaultVideoFilters,
  authorFiltersFromQuery,
  videoFiltersFromQuery,
  parseNonNegative,
} from "../../../frontend/src/utils/filters.js";
import { selectAuthors } from "../../../frontend/src/utils/selectAuthors.js";
import { selectAuthorVideos } from "../../../frontend/src/utils/selectAuthorVideos.js";
import { selectSearchVideos } from "../../../frontend/src/utils/selectSearchVideos.js";
import { buildSearchQuery } from "../../../frontend/src/utils/searchQuery.js";

describe("pre-refactor behavior characterization", () => {
  it("preserves video grouping priority, order, blank URLs and duplicate IDs", () => {
    for (const items of [
      [],
      videos,
      [...videos].reverse(),
      [
        { id: 1, original_url: "a", repost_url: "b" },
        { id: 2, original_url: "a", repost_url: "c" },
        { id: 3, original_url: "d", repost_url: "b" },
        { id: 3, original_url: "a" },
        { id: 4, original_url: " " },
        { id: 5 },
      ],
    ])
      expect(groupVideosByName(items)).toEqual(legacy.groupVideosByName(items));
  });
  it("keeps the two title ordering policies", () => {
    const titles = [
      "",
      "第1話",
      "第2話",
      "第一話",
      "第二話",
      "第九話",
      "第10話",
      "【東方】一",
      "東方2",
      "東方 二",
      "Episode 01",
      "episode 2",
      "カフェ",
      "Café",
      "Ａ・Ｂ",
      "中文",
    ];
    for (const a of titles)
      for (const b of titles) {
        expect(compareAuthorVideoTitles(a, b)).toBe(
          legacy.compareAuthorVideoTitles(a, b),
        );
        expect(compareSearchVideoTitles(a, b)).toBe(
          legacy.compareSearchVideoTitles(a, b),
        );
      }
  });
  it("preserves all pagination branches, including existing edge behavior", () => {
    for (const width of [390, 768, 769, 834, 1440])
      for (let total = 0; total <= 30; total++)
        for (let current = 1; current <= Math.max(1, total); current++) {
          expect(paginationItems(current, total, width)).toEqual(
            legacy.paginationItems(current, total, width),
          );
        }
  });
  it("preserves normalization and mixed script matching", () => {
    const texts = [
      "",
      null,
      "東方・動画【第一話】",
      "Alice ＃01！",
      "カフェ Café",
      "测试作者 001",
      "ひらがな カタカナ 漢字",
    ];
    for (const text of texts) {
      expect(normalizeTextForSearch(text)).toBe(
        legacy.normalizeTextForSearch(text),
      );
      for (const query of texts)
        expect(isTextMatch(text, query)).toBe(legacy.isTextMatch(text, query));
    }
  });
  it("preserves author sorting and duration/work boundaries without mutating input", () => {
    const before = structuredClone(authors);
    for (const filters of [
      defaultAuthorFilters(),
      { ...defaultAuthorFilters(), minWorks: 10, maxWorks: 40 },
      {
        ...defaultAuthorFilters(),
        minAverageDuration: 80,
        maxAverageDuration: 100,
      },
      {
        ...defaultAuthorFilters(),
        minAverageDuration: 80,
        includeUnknownDuration: true,
      },
    ]) {
      for (const field of ["name", "worksCount", "lastUpdate"])
        for (const order of ["asc", "desc"])
          expect(selectAuthors(authors, filters, field, order)).toEqual(
            legacy.legacyHomeView(authors, filters, field, order),
          );
    }
    expect(authors).toEqual(before);
  });
  it("preserves separate author/search tie breaking, missing dates and numeric statuses", () => {
    const items = [
      ...videos,
      { id: 100, original_name: "第二話", translation_status: "1" },
      {
        id: 101,
        original_name: "第一話",
        translation_status: 1,
        original_duration: 0,
      },
      {
        id: 102,
        original_name: "第1話",
        translation_status: 1,
        date: "invalid",
      },
    ];
    for (const filters of [
      defaultVideoFilters(),
      { ...defaultVideoFilters(), minDuration: 0, maxDuration: 60 },
      {
        ...defaultVideoFilters(),
        minDuration: 60,
        includeUnknownDuration: true,
      },
      { ...defaultVideoFilters(), translationStatus: "1" },
      {
        ...defaultVideoFilters(),
        dateFrom: "2026-10-03",
        dateTo: "2026-10-08",
      },
    ]) {
      for (const field of ["date", "translation"])
        for (const order of ["asc", "desc"])
          expect(selectAuthorVideos(items, filters, field, order)).toEqual(
            legacy.legacyVideoView(items, filters, field, order),
          );
    }
    for (const field of ["date", "translation", "relevance"])
      for (const order of ["asc", "desc"])
        expect(selectSearchVideos(items, field, order)).toEqual(
          legacy.legacySearchView(items, undefined, field, order),
        );
  });
});

describe("query compatibility", () => {
  it("uses short aliases first, including zero and empty values", () => {
    expect(
      videoFiltersFromQuery({
        minDur: "0",
        minDuration: "90",
        status: "2",
        translationStatus: "1",
        unknown: "1",
      }),
    ).toEqual({
      ...defaultVideoFilters(),
      minDuration: 0,
      translationStatus: "2",
      includeUnknownDuration: true,
    });
    expect(
      videoFiltersFromQuery({ minDuration: "90", dateFrom: "2026-01-01" }),
    ).toEqual({
      ...defaultVideoFilters(),
      minDuration: 90,
      dateFrom: "2026-01-01",
    });
    expect(
      authorFiltersFromQuery({
        minW: "0",
        maxWorks: "30",
        minAvgDuration: "60",
        includeUnknownDuration: "1",
      }),
    ).toEqual({
      ...defaultAuthorFilters(),
      minWorks: 0,
      maxWorks: 30,
      minAverageDuration: 60,
      includeUnknownDuration: true,
    });
    for (const value of [undefined, null, "", -1, "no", "Infinity"])
      expect(parseNonNegative(value)).toBeNull();
  });
  it("serializes header filters and only includes unknown with duration filtering", () => {
    const form = {
      query: " 东方 ",
      type: "videos",
      limit: 100,
      filters: {
        authorInput: "作者",
        translationStatus: "2",
        dateFrom: "2026-01-01",
        dateTo: "",
        minDuration: 0,
        maxDuration: 60,
        includeUnknownDuration: true,
      },
    };
    expect(buildSearchQuery(form, () => 7)).toEqual({
      q: "东方",
      type: "videos",
      limit: 100,
      author: 7,
      status: "2",
      from: "2026-01-01",
      minDur: 0,
      maxDur: 60,
      unknown: "1",
    });
    expect(buildSearchQuery({ ...form, type: "authors" }, () => 7)).toEqual({
      q: "东方",
      type: "authors",
      limit: 100,
    });
    expect(
      buildSearchQuery(
        {
          ...form,
          filters: { ...form.filters, minDuration: null, maxDuration: null },
        },
        () => null,
      ),
    ).toEqual({
      q: "东方",
      type: "videos",
      limit: 100,
      status: "2",
      from: "2026-01-01",
    });
  });
});
