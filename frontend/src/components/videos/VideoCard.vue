<template>
  <component
    :is="videoHref ? 'a' : 'div'"
    :href="videoHref"
    :target="videoHref ? '_blank' : undefined"
    :rel="videoHref ? 'noopener noreferrer' : undefined"
    class="video-column"
    :class="[
      columnType === 'original' ? 'original-column' : 'repost-column',
      isCompact ? 'compact-column' : '',
      isCentered ? 'centered-column' : '',
      {
        'clickable-column': effectiveVideo.url,
        'disabled-column': !effectiveVideo.url,
      },
    ]"
    @click="handleClick"
  >
    <div
      :class="columnType === 'original' ? 'original-header' : 'repost-header'"
    >
      <!-- Video thumbnail -->
      <div
        class="video-thumbnail"
        :class="{ 'compact-thumbnail': isCompact }"
        v-if="effectiveVideo.thumbnail"
      >
        <div class="thumbnail-loading">
          <v-progress-circular
            :size="isCompact ? 24 : 32"
            :width="isCompact ? 2 : 3"
            color="primary"
            indeterminate
          ></v-progress-circular>
          <span class="loading-text">{{
            isCompact ? "加载中..." : "封面加载中..."
          }}</span>
        </div>
        <img
          :src="effectiveVideo.thumbnail"
          :alt="
            effectiveVideo.name ||
            (columnType === 'original' ? '原视频' : '转载视频')
          "
          :referrerpolicy="
            needsSpecialAttributes(effectiveVideo.thumbnail)
              ? 'no-referrer'
              : null
          "
          :crossorigin="
            needsSpecialAttributes(effectiveVideo.thumbnail)
              ? 'anonymous'
              : null
          "
          @load="handleThumbnailLoad"
          @error="handleThumbnailError"
        />
        <span v-if="formattedDuration" class="video-duration">
          {{ formattedDuration }}
        </span>
      </div>

      <component
        :is="isCompact ? 'h4' : 'h3'"
        class="video-title"
        :class="{ 'compact-title': isCompact }"
      >
        {{
          effectiveVideo.name ||
          (columnType === "original" ? "暂无原视频" : "暂无转载")
        }}
      </component>

      <!-- Video source (for original videos) -->
      <div
        class="video-source"
        v-if="columnType === 'original' && effectiveVideo.url && videoSource"
      >
        <span :class="videoSource.class">
          {{ videoSource.text }}
        </span>
      </div>

      <!-- Translation status (for repost videos) -->
      <div
        class="translation-status"
        v-if="
          columnType === 'repost' && (isRepostDead || showTranslationStatus)
        "
      >
        <span :class="isRepostDead ? 'status-none' : translationStatusClass">
          {{ isRepostDead ? "转载失效" : translationStatusText }}
        </span>
      </div>
    </div>
  </component>
</template>

<script setup>
import { useVideoCard } from "@/composables/useVideoCard.js";

const props = defineProps({
  video: {
    type: Object,
    required: true,
  },
  columnType: {
    type: String,
    required: true,
    validator: (value) => ["original", "repost"].includes(value),
  },
  isCompact: {
    type: Boolean,
    default: false,
  },
  isCentered: {
    type: Boolean,
    default: false,
  },
  comment: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["click"]);

const {
  effectiveVideo,
  formattedDuration,
  videoHref,
  handleClick,
  videoSource,
  showTranslationStatus,
  translationStatusText,
  translationStatusClass,
  isRepostDead,
  needsSpecialAttributes,
  handleThumbnailLoad,
  handleThumbnailError,
} = useVideoCard(props, emit);
</script>

<style scoped>
.video-column {
  display: block;
  color: inherit;
  text-decoration: none;
  background: var(--color-surface-1); /* Catppuccin Mocha Surface1 */
  border-radius: 10px;
  padding: 16px;
  border: 1px solid var(--color-surface-2);
  transition: all 0.3s ease;
  min-width: 0; /* Prevent grid item from overflowing its column */
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
  background: var(--color-surface-2); /* Catppuccin Mocha Surface2 */
  box-shadow: 0 4px 16px var(--color-mauve-30);
  transform: translateY(-3px);
  border-color: var(--color-overlay);
}

.clickable-column:hover .video-title {
  color: var(--color-sapphire); /* Catppuccin Mocha Sapphire */
  text-shadow: 0 1px 2px var(--color-black-30);
}

/* Non-clickable column styles */
.disabled-column {
  opacity: 0.7;
  cursor: not-allowed;
}

.disabled-column .video-title {
  color: var(--color-overlay); /* Catppuccin Mocha Overlay0 */
  font-style: italic;
}

.original-column {
  border-left: 4px solid var(--color-blue); /* Catppuccin Mocha Blue */
}

.repost-column {
  border-left: 4px solid var(--color-green); /* Catppuccin Mocha Green */
}

.video-thumbnail {
  width: 100%;
  height: 300px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-surface-2); /* Catppuccin Mocha Surface2 */
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
  background: var(--color-surface-2);
  z-index: 1;
  gap: 12px;
}

.loading-text {
  color: var(--color-text-muted); /* Catppuccin Mocha Subtext0 */
  font-size: 0.9rem;
  text-align: center;
}

.error-text {
  color: var(--color-red); /* Catppuccin Mocha Red */
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

.video-duration {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 2;
  padding: 2px 5px;
  border-radius: 4px;
  color: var(--color-white);
  background: var(--color-deep-shadow-82);
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}

.clickable-column:hover .video-thumbnail img {
  transform: scale(1.05);
}

.video-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-text); /* Catppuccin Mocha Text */
  line-height: 1.4;
  transition: all 0.2s ease;
  overflow-wrap: break-word; /* Break long URLs/unbroken strings */
  word-break: break-word;
}

.compact-title {
  font-size: 0.9rem;
  line-height: 1.3;
}

.clickable-column .video-title {
  color: var(--color-blue); /* Catppuccin Mocha Blue */
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
  color: var(--color-red);
  background: var(--color-red-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-red-30);
}

.status-full {
  color: var(--color-green);
  background: var(--color-green-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-green-30);
}

.status-partial {
  color: var(--color-yellow);
  background: var(--color-yellow-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-yellow-30);
}

.status-unknown {
  color: var(--color-overlay);
  background: var(--color-overlay-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-overlay-30);
}

/* Video source styles */
.source-youtube {
  color: var(--color-red);
  background: var(--color-red-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-red-30);
}

.source-niconico {
  color: var(--color-peach);
  background: var(--color-peach-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-peach-30);
}

.source-bilibili {
  color: var(--color-blue);
  background: var(--color-blue-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-blue-30);
}

.source-twitter {
  color: var(--color-sapphire);
  background: var(--color-sapphire-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-sapphire-30);
}

.source-other {
  color: var(--color-mauve);
  background: var(--color-mauve-15);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid var(--color-mauve-30);
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
