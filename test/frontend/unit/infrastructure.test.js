import { afterEach, describe, expect, it, vi } from "vitest";
import { API_URLS } from "../../../frontend/src/config/api.js";
import {
  fetchAuthors,
  fetchStats,
  fetchAuthorVideos,
  fetchSearchResults,
} from "../../../frontend/src/services/api.js";
import { buildSearchParams } from "../../../frontend/src/utils/searchQuery.js";
import { formatVideoDuration } from "../../../frontend/src/utils/videoDuration.js";
import { useSortControl } from "../../../frontend/src/composables/useSortControl.js";

afterEach(() => vi.unstubAllGlobals());

it("keeps API paths and leaves HTTP errors for the caller to interpret", async () => {
  const response = { ok: false, status: 500 };
  const fetch = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetch);
  expect(await fetchAuthors()).toBe(response);
  expect(fetch).toHaveBeenLastCalledWith(API_URLS.AUTHORS);
  await fetchStats();
  expect(fetch).toHaveBeenLastCalledWith(API_URLS.STATS);
  await fetchAuthorVideos("12");
  expect(fetch).toHaveBeenLastCalledWith(
    `${API_URLS.AUTHORS.replace("/authors", "")}/author/12/videos`,
  );
  const params = buildSearchParams("东方", {
    minDur: "0",
    maxDuration: "60",
    status: "2",
    unknown: "1",
  });
  await fetchSearchResults("videos", params);
  expect(fetch).toHaveBeenLastCalledWith(
    `${API_URLS.SEARCH_VIDEOS}?q=%E4%B8%9C%E6%96%B9&limit=100&translationStatus=2&minDuration=0&maxDuration=60&includeUnknownDuration=1`,
  );
  await fetchSearchResults("authors", new URLSearchParams({ q: "Alice" }));
  expect(fetch).toHaveBeenLastCalledWith(`${API_URLS.SEARCH_AUTHORS}?q=Alice`);
  fetch.mockRejectedValueOnce(new TypeError("network failure"));
  await expect(fetchAuthors()).rejects.toThrow("network failure");
});

it("preserves video duration labels, rounding and unknown values", () => {
  for (const value of [null, undefined, "", -1, "bad", Infinity])
    expect(formatVideoDuration(value)).toBe("");
  for (const [value, label] of [
    [0, "0:00"],
    [59.6, "1:00"],
    [3599, "59:59"],
    [3600, "1:00:00"],
    ["61", "1:01"],
  ])
    expect(formatVideoDuration(value)).toBe(label);
});

describe("sort control event contracts", () => {
  it("keeps home defaults and emits updates before the sort-change event", () => {
    const emit = vi.fn();
    const props = { sortBy: "name", sortOrder: "asc" };
    const select = useSortControl(props, emit, {
      defaultOrder: (field) => (field === "name" ? "asc" : "desc"),
    });
    select("worksCount");
    expect(emit.mock.calls).toEqual([
      ["update:sortBy", "worksCount"],
      ["update:sortOrder", "desc"],
      ["sort-change", { sortBy: "worksCount", sortOrder: "desc" }],
    ]);
    emit.mockClear();
    select("name");
    expect(emit.mock.calls[1]).toEqual(["update:sortOrder", "desc"]);
  });
  it("keeps the search sortType prop and ascending default", () => {
    const emit = vi.fn();
    useSortControl({ sortType: "relevance", sortOrder: "desc" }, emit, {
      fieldProp: "sortType",
    })("date");
    expect(emit.mock.calls).toEqual([
      ["update:sortType", "date"],
      ["update:sortOrder", "asc"],
      ["sort-change", { sortType: "date", sortOrder: "asc" }],
    ]);
  });
});
