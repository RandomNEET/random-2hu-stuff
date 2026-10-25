export const image = "https://fixtures.invalid/image.svg";
export const authors = Array.from({ length: 100 }, (_, index) => ({
  id: index + 1,
  yt_name: `测试作者 ${String(index + 1).padStart(3, "0")}`,
  nico_name: index === 0 ? "ニコ作者" : "",
  twitter_name: "",
  nico_avatar: image,
  yt_avatar: image,
  yt_url: `https://youtube.com/@author${index + 1}`,
  nico_url: index === 0 ? "https://nicovideo.jp/user/1" : "",
  worksCount: index + 1,
  averageDuration: index % 5 === 0 ? null : 60 + index,
  lastUpdate: `2026-10-${String((index % 18) + 1).padStart(2, "0")}`,
  comment: index === 0 ? "作者备注 https://example.com" : "",
}));
export const videos = Array.from({ length: 46 }, (_, index) => ({
  id: index + 1,
  author_id: 1,
  yt_name: authors[0].yt_name,
  nico_avatar: image,
  original_name: `东方视频 第${index + 1}话`,
  original_url: `https://youtube.com/watch?v=video${index + 1}`,
  original_thumbnail: image,
  original_duration: index % 5 === 0 ? null : index * 30,
  repost_name: `中文字幕 ${index + 1}`,
  repost_url: `https://bilibili.com/video/BVfixture${index + 1}`,
  repost_thumbnail: image,
  repost_duration: null,
  translation_status: index % 6 || null,
  date:
    index % 8 === 0
      ? null
      : `2026-10-${String((index % 18) + 1).padStart(2, "0")}`,
  comment: index === 4 ? "原视频已删除" : "",
}));
videos[1].original_url = videos[0].original_url;
videos[3].repost_url = videos[2].repost_url;
videos[5].original_url = null;
videos[5].repost_url = null;

export async function mockApi(page, { empty = false, fail = false } = {}) {
  await page.route("https://**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.startsWith("/api/")) {
      if (fail) return route.fulfill({ status: 500, json: {} });
      const data =
        url.pathname === "/api/stats"
          ? { maxVideoDuration: 3600 }
          : url.pathname.includes("videos")
            ? videos
            : authors;
      return route.fulfill({ json: empty && Array.isArray(data) ? [] : data });
    }
    if (url.hostname === "api.bilibili.com") {
      const callback = url.searchParams.get("callback");
      return route.fulfill({
        contentType: "application/javascript",
        body: `${callback}({code: 0})`,
      });
    }
    if (url.hostname === "fixtures.invalid") {
      return route.fulfill({
        contentType: "image/svg+xml",
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#45475a"/><circle cx="160" cy="90" r="40" fill="#cba6f7"/></svg>',
      });
    }
    if (route.request().isNavigationRequest())
      return route.fulfill({
        contentType: "text/html",
        body: "<title>External link fixture</title>",
      });
    return route.abort();
  });
}
