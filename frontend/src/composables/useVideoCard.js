import { computed } from "vue";
import { useBilibiliAvailability } from "./useBilibiliAvailability.js";
import { formatVideoDuration } from "@/utils/videoDuration.js";
import {
  needsSpecialAttributes,
  handleThumbnailLoad,
  handleThumbnailError,
} from "@/utils/thumbnails.js";

export function useVideoCard(props, emit) {
  const isOriginalDeleted = computed(() => {
    const deleteKeywords = [
      "已删除",
      "删除",
      "已隐藏",
      "隐藏",
      "已失效",
      "失效",
      "已注销",
      "注销",
      "非公开",
      "地域限制",
      "区域限制",
      "版权限制",
      "专享",
      "私享",
      "无法播放",
      "无补档",
    ];
    return (
      props.columnType === "original" &&
      props.comment &&
      deleteKeywords.some((kw) => props.comment.includes(kw))
    );
  });

  const { isRepostDead } = useBilibiliAvailability(props);

  const effectiveVideo = computed(() => ({
    name: isOriginalDeleted.value ? "" : props.video.name,
    url: isOriginalDeleted.value ? null : props.video.url,
    thumbnail: props.video.thumbnail,
    duration: props.video.duration,
    translationStatus: props.video.translationStatus,
  }));

  const formattedDuration = computed(() => formatVideoDuration(effectiveVideo.value.duration));

  const videoHref = computed(() => {
    const url = effectiveVideo.value.url;
    return url ? (url.startsWith("http") ? url : `https://${url}`) : undefined;
  });

  const handleClick = (event) => {
    if (videoHref.value) {
      // Let the browser handle modified clicks using the native link.
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      emit("click", props.video.url);
    }
  };

  // Video source helpers
  const videoSource = computed(() => {
    if (!effectiveVideo.value.url) return null;

    const lowerUrl = effectiveVideo.value.url.toLowerCase();

    if (lowerUrl.includes("youtube.com") || lowerUrl.includes("youtu.be")) {
      return { text: "YouTube", class: "source-youtube" };
    } else if (
      lowerUrl.includes("nicovideo.jp") ||
      lowerUrl.includes("nico.ms")
    ) {
      return { text: "NicoNico", class: "source-niconico" };
    } else if (lowerUrl.includes("bilibili.com")) {
      return { text: "Bilibili", class: "source-bilibili" };
    } else if (lowerUrl.includes("twitter.com") || lowerUrl.includes("x.com")) {
      return { text: "Twitter/X", class: "source-twitter" };
    } else {
      return { text: "其他", class: "source-other" };
    }
  });

  // Translation status helpers
  const showTranslationStatus = computed(() => {
    return (
      effectiveVideo.value.translationStatus !== null &&
      effectiveVideo.value.translationStatus !== "" &&
      translationStatusText.value !== ""
    );
  });

  const translationStatusText = computed(() => {
    switch (effectiveVideo.value.translationStatus) {
      case 1:
        return "中文内嵌";
      case 2:
        return "CC字幕";
      case 3:
        return "弹幕翻译";
      case 4:
        return "无需翻译";
      case 5:
        return "暂无翻译";
      default:
        return "";
    }
  });

  const translationStatusClass = computed(() => {
    switch (effectiveVideo.value.translationStatus) {
      case 1:
      case 2:
      case 4:
        return "status-full";
      case 3:
        return "status-partial";
      case 5:
        return "status-none";
      default:
        return "status-unknown";
    }
  });

  return { effectiveVideo, formattedDuration, videoHref, handleClick, videoSource, showTranslationStatus, translationStatusText, translationStatusClass, isRepostDead, needsSpecialAttributes, handleThumbnailLoad, handleThumbnailError };
}
