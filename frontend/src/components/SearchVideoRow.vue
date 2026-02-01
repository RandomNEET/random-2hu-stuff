<template>
  <div class="video-row">
    <div class="video-header-row">
      <div class="video-info-section">
        <div class="left-info">
          <div class="video-date" v-if="video.date">
            📅 {{ formatDate(video.date) }}
          </div>

          <div class="video-comment" v-if="video.comment">
            {{ video.comment }}
          </div>
        </div>

        <div class="author-info-small" @click="handleAuthorClick">
          <v-avatar size="24" class="author-avatar-small">
            <v-img :src="authorAvatar" />
          </v-avatar>
          <span class="author-name-small">{{ authorName }}</span>
        </div>
      </div>
    </div>

    <div class="video-columns">
      <VideoCard
        :video="{
          name: video.original_name,
          url: video.original_url,
          thumbnail: video.original_thumbnail
        }"
        column-type="original"
        @click="openUrl"
      />
      <VideoCard
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
</template>

<script setup>
import { computed } from 'vue';
import VideoCard from './VideoCard.vue';

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['author-click']);

const authorName = computed(() => {
  return props.video.yt_name || props.video.nico_name || props.video.twitter_name || "Unknown";
});

const authorAvatar = computed(() => {
  return props.video.nico_avatar || props.video.yt_avatar || props.video.twitter_avatar;
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

const handleAuthorClick = () => {
  emit('author-click', props.video.author_id, authorName.value);
};

const openUrl = (url) => {
  if (url) {
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};
</script>

<style scoped>
.video-row {
  background: #313244; /* Catppuccin Mocha Surface0 */
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #45475a;
  transition: all 0.3s ease;
}

.video-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}

.video-info-section {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.left-info {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.video-date {
  font-size: 0.9rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  background: #585b70; /* Catppuccin Mocha Surface2 */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
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

.author-info-small {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(137, 180, 250, 0.1);
}

.author-info-small:hover {
  background: rgba(137, 180, 250, 0.2);
  transform: scale(1.05);
}

.author-name-small {
  color: #89b4fa; /* Catppuccin Mocha Blue */
  font-size: 0.9rem;
  font-weight: 600;
}

.author-avatar-small {
  border: 1px solid #585b70;
}

.video-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* Responsive design */
@media (max-width: 834px) {
  .video-row {
    padding: 16px;
  }

  .video-header-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .video-info-section {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  .left-info {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  .video-columns {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .video-row {
    padding: 12px;
  }

  .video-info-section {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }

  .left-info {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
  }

  .video-columns {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .video-comment {
    font-size: 0.8rem;
    padding: 4px 8px;
  }
}

@media (max-width: 360px) {
  .video-info-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .author-info-small {
    align-self: flex-end;
  }
}
</style>
