<template>
  <div
    class="video-column"
    :class="[
      columnType === 'original' ? 'original-column' : 'repost-column',
      isCompact ? 'compact-column' : '',
      isCentered ? 'centered-column' : '',
      {
        'clickable-column': video.url,
        'disabled-column': !video.url
      }
    ]"
    @click="handleClick"
  >
    <div :class="columnType === 'original' ? 'original-header' : 'repost-header'">
      <!-- Video thumbnail -->
      <div
        class="video-thumbnail"
        :class="{ 'compact-thumbnail': isCompact }"
        v-if="video.thumbnail"
      >
        <div class="thumbnail-loading">
          <v-progress-circular
            :size="isCompact ? 24 : 32"
            :width="isCompact ? 2 : 3"
            color="primary"
            indeterminate
          ></v-progress-circular>
          <span class="loading-text">{{ isCompact ? '加载中...' : '封面加载中...' }}</span>
        </div>
        <img
          :src="video.thumbnail"
          :alt="video.name || (columnType === 'original' ? '原视频' : '转载视频')"
          :referrerpolicy="needsSpecialAttributes(video.thumbnail) ? 'no-referrer' : null"
          :crossorigin="needsSpecialAttributes(video.thumbnail) ? 'anonymous' : null"
          @load="handleThumbnailLoad"
          @error="handleThumbnailError"
        />
      </div>

      <component :is="isCompact ? 'h4' : 'h3'" class="video-title" :class="{ 'compact-title': isCompact }">
        {{ video.name || (columnType === 'original' ? '暂无原视频' : '暂无转载') }}
      </component>

      <!-- Video source (for original videos) -->
      <div
        class="video-source"
        v-if="columnType === 'original' && video.url && videoSource"
      >
        <span :class="videoSource.class">
          {{ videoSource.text }}
        </span>
      </div>

      <!-- Translation status (for repost videos) -->
      <div
        class="translation-status"
        v-if="columnType === 'repost' && showTranslationStatus"
      >
        <span :class="translationStatusClass">
          {{ translationStatusText }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  video: {
    type: Object,
    required: true
  },
  columnType: {
    type: String,
    required: true,
    validator: (value) => ['original', 'repost'].includes(value)
  },
  isCompact: {
    type: Boolean,
    default: false
  },
  isCentered: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['click']);

const handleClick = () => {
  if (props.video.url) {
    emit('click', props.video.url);
  }
};

// Video source helpers
const videoSource = computed(() => {
  if (!props.video.url) return null;

  const lowerUrl = props.video.url.toLowerCase();

  if (lowerUrl.includes("youtube.com") || lowerUrl.includes("youtu.be")) {
    return { text: "YouTube", class: "source-youtube" };
  } else if (lowerUrl.includes("nicovideo.jp") || lowerUrl.includes("nico.ms")) {
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
  return props.video.translationStatus !== null &&
         props.video.translationStatus !== '' &&
         translationStatusText.value !== '';
});

const translationStatusText = computed(() => {
  switch (props.video.translationStatus) {
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
  switch (props.video.translationStatus) {
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

// Determine if image needs special loading attributes
const needsSpecialAttributes = (imageUrl) => {
  if (!imageUrl) return false;
  const lowerUrl = imageUrl.toLowerCase();
  return lowerUrl.includes("hdslb.com");
};

// Thumbnail loading handlers
const handleThumbnailLoad = (event) => {
  event.target.style.opacity = "1";
  const loadingElement = event.target.previousElementSibling;
  if (loadingElement && loadingElement.classList.contains("thumbnail-loading")) {
    loadingElement.style.display = "none";
  }
};

const handleThumbnailError = (event) => {
  event.target.style.display = "none";
  const loadingElement = event.target.previousElementSibling;
  if (loadingElement && loadingElement.classList.contains("thumbnail-loading")) {
    loadingElement.innerHTML = '<span class="error-text">封面加载失败</span>';
    loadingElement.style.color = "#f38ba8";
  }
};
</script>

<style scoped>
.video-column {
  background: #45475a; /* Catppuccin Mocha Surface1 */
  border-radius: 10px;
  padding: 16px;
  border: 1px solid #585b70;
  transition: all 0.3s ease;
}

/* Compact column styles for grouped items */
.compact-column {
  padding: 10px;
  margin-bottom: 0;
}

/* Centered column for single items in grouped layout */
.centered-column {
  display: flex;
  align-items: center;
  min-height: 100%;
}

.centered-column .original-header,
.centered-column .repost-header {
  width: 100%;
}

/* Clickable column styles */
.clickable-column {
  cursor: pointer;
}

.clickable-column:hover {
  background: #585b70; /* Catppuccin Mocha Surface2 */
  box-shadow: 0 4px 16px rgba(203, 166, 247, 0.3);
  transform: translateY(-3px);
  border-color: #6c7086;
}

.clickable-column:hover .video-title {
  color: #74c7ec; /* Catppuccin Mocha Sapphire */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

/* Non-clickable column styles */
.disabled-column {
  opacity: 0.7;
  cursor: not-allowed;
}

.disabled-column .video-title {
  color: #6c7086; /* Catppuccin Mocha Overlay0 */
  font-style: italic;
}

.original-column {
  border-left: 4px solid #89b4fa; /* Catppuccin Mocha Blue */
}

.repost-column {
  border-left: 4px solid #a6e3a1; /* Catppuccin Mocha Green */
}

.video-thumbnail {
  width: 100%;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  background: #585b70; /* Catppuccin Mocha Surface2 */
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  position: relative;
}

.compact-thumbnail {
  height: 120px;
  margin-bottom: 8px;
}

.thumbnail-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #585b70;
  z-index: 1;
  gap: 12px;
}

.loading-text {
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  font-size: 0.9rem;
  text-align: center;
}

.error-text {
  color: #f38ba8; /* Catppuccin Mocha Red */
  font-size: 0.9rem;
  text-align: center;
}

.video-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition:
    transform 0.3s ease,
    opacity 0.3s ease;
  opacity: 0;
  position: absolute;
  top: 0;
  left: 0;
}

.clickable-column:hover .video-thumbnail img {
  transform: scale(1.05);
}

.video-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: #cdd6f4; /* Catppuccin Mocha Text */
  line-height: 1.4;
  transition: all 0.2s ease;
}

.compact-title {
  font-size: 0.9rem;
  line-height: 1.3;
}

.clickable-column .video-title {
  color: #89b4fa; /* Catppuccin Mocha Blue */
}

.repost-header,
.original-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.compact-column .repost-header,
.compact-column .original-header {
  gap: 8px;
}

.video-source {
  align-self: flex-start;
}

.translation-status {
  align-self: flex-start;
}

/* Status styles */
.status-none {
  color: #f38ba8;
  background: rgba(243, 139, 168, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(243, 139, 168, 0.3);
}

.status-full {
  color: #a6e3a1;
  background: rgba(166, 227, 161, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(166, 227, 161, 0.3);
}

.status-partial {
  color: #f9e2af;
  background: rgba(249, 226, 175, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(249, 226, 175, 0.3);
}

.status-unknown {
  color: #6c7086;
  background: rgba(108, 112, 134, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(108, 112, 134, 0.3);
}

/* Video source styles */
.source-youtube {
  color: #f38ba8;
  background: rgba(243, 139, 168, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(243, 139, 168, 0.3);
}

.source-niconico {
  color: #fab387;
  background: rgba(250, 179, 135, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(250, 179, 135, 0.3);
}

.source-bilibili {
  color: #89b4fa;
  background: rgba(137, 180, 250, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(137, 180, 250, 0.3);
}

.source-twitter {
  color: #74c7ec;
  background: rgba(116, 199, 236, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(116, 199, 236, 0.3);
}

.source-other {
  color: #cba6f7;
  background: rgba(203, 166, 247, 0.15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid rgba(203, 166, 247, 0.3);
}

/* Responsive design */
@media (max-width: 834px) {
  .video-column {
    padding: 12px;
  }

  .video-title {
    font-size: 0.95rem;
  }

  .video-thumbnail {
    height: 200px;
  }

  .compact-thumbnail {
    height: 80px;
  }

  .compact-title {
    font-size: 0.8rem;
  }

  .repost-header,
  .original-header {
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .video-column {
    padding: 8px;
  }

  .video-title {
    font-size: 0.85rem;
    line-height: 1.3;
  }

  .video-thumbnail {
    height: 80px;
  }

  .compact-column {
    padding: 6px;
  }

  .compact-thumbnail {
    height: 60px;
    margin-bottom: 4px;
  }

  .compact-title {
    font-size: 0.75rem;
    line-height: 1.2;
  }

  .status-none,
  .status-full,
  .status-partial,
  .status-unknown,
  .source-youtube,
  .source-niconico,
  .source-bilibili,
  .source-twitter,
  .source-other {
    font-size: 0.7rem;
    padding: 2px 6px;
  }
}
</style>
