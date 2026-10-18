/** Preserve input order and prefer shared original URLs over repost URLs. */
export const groupVideosByName = (videoList) => {
  const groups = [];
  const processedVideos = new Set();

  videoList.forEach((video) => {
    if (processedVideos.has(video.id)) return;

    const group = {
      id: video.id,
      date: video.date,
      comment: video.comment,
      type: "single",
      videos: [video],
      displayOriginal: null,
      displayRepost: null,
      additionalOriginals: [],
      additionalReposts: [],
    };

    if (video.original_url && video.original_url.trim()) {
      const sameOriginalVideos = videoList.filter(
        (v) =>
          !processedVideos.has(v.id) &&
          v.original_url === video.original_url &&
          v.id !== video.id,
      );

      if (sameOriginalVideos.length > 0) {
        group.type = "original_group";
        group.displayOriginal = video;
        group.additionalReposts = [video, ...sameOriginalVideos];

        processedVideos.add(video.id);
        sameOriginalVideos.forEach((v) => processedVideos.add(v.id));

        groups.push(group);
        return;
      }
    }

    if (video.repost_url && video.repost_url.trim()) {
      const sameRepostVideos = videoList.filter(
        (v) =>
          !processedVideos.has(v.id) &&
          v.repost_url === video.repost_url &&
          v.id !== video.id,
      );

      if (sameRepostVideos.length > 0) {
        group.type = "repost_group";
        group.displayRepost = video;
        group.additionalOriginals = [video, ...sameRepostVideos];

        processedVideos.add(video.id);
        sameRepostVideos.forEach((v) => processedVideos.add(v.id));

        groups.push(group);
        return;
      }
    }

    processedVideos.add(video.id);
    groups.push(group);
  });

  return groups;
};
