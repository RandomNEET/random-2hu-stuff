<template>
  <div class="video-row">
    <div class="video-info-row">
      <div class="video-date" v-if="group.date">
        📅 {{ formatDate(group.date) }}
      </div>

      <div class="video-comment" v-if="group.comment">
        {{ group.comment }}
      </div>
    </div>

    <!-- Single video display (no grouping) -->
    <div v-if="group.type === 'single'" class="video-columns">
      <VideoCard
        :video="{
          name: group.videos[0].original_name,
          url: group.videos[0].original_url,
          thumbnail: group.videos[0].original_thumbnail
        }"
        column-type="original"
        @click="openUrl"
      />
      <VideoCard
        :video="{
          name: group.videos[0].repost_name,
          url: group.videos[0].repost_url,
          thumbnail: group.videos[0].repost_thumbnail,
          translationStatus: group.videos[0].translation_status
        }"
        column-type="repost"
        @click="openUrl"
      />
    </div>

    <!-- Original group display (one original, multiple reposts) -->
    <div
      v-else-if="group.type === 'original_group'"
      class="video-columns grouped-columns"
    >
      <VideoCard
        :video="{
          name: group.displayOriginal.original_name,
          url: group.displayOriginal.original_url,
          thumbnail: group.displayOriginal.original_thumbnail
        }"
        column-type="original"
        is-centered
        @click="openUrl"
      />

      <div class="repost-area">
        <div class="repost-list">
          <VideoCard
            v-for="video in group.additionalReposts"
            :key="`repost-${video.id}`"
            :video="{
              name: video.repost_name,
              url: video.repost_url,
              thumbnail: video.repost_thumbnail,
              translationStatus: video.translation_status
            }"
            column-type="repost"
            @click="openUrl"
          />
        </div>
      </div>
    </div>

    <!-- Repost group display (one repost, multiple originals) -->
    <div
      v-else-if="group.type === 'repost_group'"
      class="video-columns grouped-columns"
    >
      <div class="original-area">
        <div class="original-list">
          <VideoCard
            v-for="video in group.additionalOriginals"
            :key="`original-${video.id}`"
            :video="{
              name: video.original_name,
              url: video.original_url,
              thumbnail: video.original_thumbnail
            }"
            column-type="original"
            @click="openUrl"
          />
        </div>
      </div>

      <VideoCard
        :video="{
          name: group.displayRepost.repost_name,
          url: group.displayRepost.repost_url,
          thumbnail: group.displayRepost.repost_thumbnail,
          translationStatus: group.displayRepost.translation_status
        }"
        column-type="repost"
        is-centered
        @click="openUrl"
      />
    </div>
  </div>
</template>

<script setup>
import VideoCard from './VideoCard.vue';

const props = defineProps({
  group: {
    type: Object,
    required: true
  }
});

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return dateStr;
  }
};

const openUrl = (url) => {
  if (url) {
    // Ensure URL has protocol prefix
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;

    // Check if we're on mobile
    const isMobile =
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent,
      );

    if (isMobile) {
      // On mobile, use location.href for direct app redirection
      window.location.href = fullUrl;
    } else {
      // For desktop, use window.open
      window.open(fullUrl, "_blank", "noopener,noreferrer");
    }
  }
};
</script>

<style scoped>
.video-row {
  background: #313244; /* Catppuccin Mocha Surface0 */
  border-radius: 12px;
  margin-bottom: 16px;
  padding: 20px;
  border: 1px solid #45475a;
  transition: all 0.3s ease;
}

.video-date {
  font-size: 0.9rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  background: #585b70; /* Catppuccin Mocha Surface2 */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
}

.video-info-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.video-comment {
  font-size: 0.9rem;
  color: #f2cdcd; /* Catppuccin Mocha Flamingo */
  background: rgba(242, 205, 205, 0.15);
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
  border: 1px solid rgba(242, 205, 205, 0.3);
  font-style: italic;
}

.video-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* Grouped columns layout */
.grouped-columns {
  grid-template-columns: 1fr 1fr;
  align-items: center;
}

.grouped-columns .original-area,
.grouped-columns .repost-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.original-list,
.repost-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Responsive design */
@media (max-width: 834px) {
  .video-row {
    padding: 16px;
  }

  .video-columns {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .grouped-columns {
    grid-template-columns: 1fr 1fr;
  }

  .video-info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .video-row {
    padding: 12px;
  }

  .video-columns {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .grouped-columns {
    grid-template-columns: 1fr 1fr;
  }

  .video-comment {
    font-size: 0.8rem;
    padding: 4px 8px;
  }
}
</style>
