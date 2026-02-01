<template>
  <div
    class="card-item"
    @click="$router.push(`/author/${author.id}`)"
  >
    <!-- Avatar as background -->
    <div
      class="avatar-background"
      :style="{
        backgroundImage: getDisplayAvatar(author)
          ? `url(${getDisplayAvatar(author)})`
          : 'none',
      }"
    ></div>

    <!-- Acrylic glass overlay -->
    <div class="acrylic-overlay"></div>

    <!-- External link button in top-left corner -->
    <div
      v-if="getDisplayUrl(author)"
      class="url-button-container"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <v-btn
        icon
        size="small"
        class="url-button-top-left"
        @click.stop="handleUrlClick(author)"
        :title="
          hasMultipleUrls(author)
            ? '访问作者频道'
            : `访问${
                author.yt_url
                  ? 'YouTube'
                  : author.nico_url
                    ? 'NicoNico'
                    : author.twitter_url
                      ? 'Twitter'
                      : '作者'
              }频道`
        "
      >
        <v-icon size="16">mdi-open-in-new</v-icon>
      </v-btn>

      <!-- Show platform-specific buttons when hovering and has multiple URLs -->
      <div
        v-if="hasMultipleUrls(author) && isHovered"
        class="platform-buttons"
      >
        <v-btn
          v-if="author.yt_url"
          icon
          size="small"
          class="platform-btn youtube-btn"
          @click.stop="openSpecificUrl(author.yt_url)"
          title="YouTube频道"
        >
          <v-icon size="14">mdi-youtube</v-icon>
        </v-btn>
        <v-btn
          v-if="author.nico_url"
          icon
          size="small"
          class="platform-btn nico-btn"
          @click.stop="openSpecificUrl(author.nico_url)"
          title="NicoNico频道"
        >
          <img
            src="https://www.nicovideo.jp/favicon.ico"
            alt="NicoNico"
            style="width: 14px; height: 14px"
          />
        </v-btn>
        <v-btn
          v-if="author.twitter_url"
          icon
          size="small"
          class="platform-btn twitter-btn"
          @click.stop="openSpecificUrl(author.twitter_url)"
          title="Twitter频道"
        >
          <v-icon size="14">mdi-twitter</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- Info section in center -->
    <div class="info-section">
      <div class="name">{{ getDisplayName(author) }}</div>
    </div>

    <!-- Video count in bottom-right corner -->
    <div class="works">📊 {{ author.worksCount }} 视频</div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  author: {
    type: Object,
    required: true
  }
});

const isHovered = ref(false);

// Helper function to get display name based on priority
const getDisplayName = (author) => {
  return author.yt_name || author.nico_name || author.twitter_name || "Unknown";
};

// Helper function to get display URL based on priority
const getDisplayUrl = (author) => {
  return author.yt_url || author.nico_url || author.twitter_url;
};

// Helper function to get display avatar based on priority
const getDisplayAvatar = (author) => {
  return author.nico_avatar || author.yt_avatar || author.twitter_avatar;
};

// Check if author has multiple URLs
const hasMultipleUrls = (author) => {
  if (!author) return false;
  const urlCount = [author.yt_url, author.nico_url, author.twitter_url].filter(
    Boolean,
  ).length;
  return urlCount > 1;
};

// Handle URL button click - direct navigation if only one URL
const handleUrlClick = (author) => {
  if (!hasMultipleUrls(author)) {
    const url = getDisplayUrl(author);
    if (url) {
      openUrl(url);
    }
  }
  // If has multiple URLs, do nothing on click - let hover handle it
};

// Open specific URL (YouTube or NicoNico)
const openSpecificUrl = (url) => {
  if (url) {
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};

const openUrl = (url) => {
  if (url) {
    // Ensure URL has protocol prefix
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};
</script>

<style scoped>
.card-item {
  position: relative;
  aspect-ratio: 1;
  /* Square card layout */
  border-radius: 20px;
  /* Rounded corners */
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  /* Default background for cards without avatar */
  background: linear-gradient(
    135deg,
    #1e1e2e 0%,
    #313244 100%
  ); /* Catppuccin Mocha Base to Surface0 */
}

.card-item:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 16px 48px rgba(203, 166, 247, 0.4);
  border-color: rgba(203, 166, 247, 0.6); /* Brighter border on hover */
}

/* Avatar background */
.avatar-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: transform 0.3s ease;
}

.card-item:hover .avatar-background {
  transform: scale(1.1);
}

/* Acrylic glass overlay */
.acrylic-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(30, 30, 46, 0.4);
  /* Adjust transparency to ensure text readability */
  backdrop-filter: blur(4px) saturate(1.2);
  /* Reduce blur intensity */
  -webkit-backdrop-filter: blur(4px) saturate(1.2);
}

/* External link button in top-left corner */
.url-button-container {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.url-button-top-left {
  background-color: rgba(30, 30, 46, 0.9) !important;
  color: #89b4fa !important;
  /* Catppuccin Mocha Blue */
  transition: all 0.3s ease;
  backdrop-filter: blur(12px);
  border: 2px solid rgba(137, 180, 250, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.url-button-top-left:hover {
  background-color: rgba(137, 180, 250, 0.2) !important;
  color: #74c7ec !important;
  /* Catppuccin Mocha Sapphire */
  transform: scale(1.15);
  border-color: rgba(116, 199, 236, 0.6);
  box-shadow: 0 4px 20px rgba(137, 180, 250, 0.5);
}

/* Platform-specific buttons */
.platform-buttons {
  display: flex;
  flex-direction: row;
  gap: 8px;
  opacity: 0;
  transform: translateX(-10px);
  animation: slideInFade 0.3s ease-out forwards;
}

@keyframes slideInFade {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.platform-btn {
  background-color: rgba(30, 30, 46, 0.9) !important;
  color: #89b4fa !important;
  transition: all 0.3s ease;
  backdrop-filter: blur(12px);
  border: 2px solid rgba(137, 180, 250, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.platform-btn:hover {
  background-color: rgba(137, 180, 250, 0.2) !important;
  color: #74c7ec !important;
  transform: scale(1.15);
  border-color: rgba(116, 199, 236, 0.6);
  box-shadow: 0 4px 20px rgba(137, 180, 250, 0.5);
}

.youtube-btn {
  color: #ff0000 !important;
}

.youtube-btn:hover {
  color: #ff3333 !important;
}

.nico-btn {
  color: #ff6b00 !important;
}

.nico-btn:hover {
  color: #ff8533 !important;
}

.twitter-btn {
  color: #1da1f2 !important;
}

.twitter-btn:hover {
  color: #4db6f7 !important;
}

/* Info section styling - occupies entire card, centered display */
.info-section {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  z-index: 5;
  padding: 20px;
}

.name {
  font-weight: bold;
  font-size: 1.4rem;
  color: #f9e2af;
  /* Catppuccin Mocha Yellow */
  margin-bottom: 12px;
  line-height: 1.2;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
  /* Reduce text shadow */
}

.works {
  position: absolute;
  /* Position to bottom-right corner */
  bottom: 12px;
  right: 12px;
  color: #cba6f7;
  /* Catppuccin Mocha Mauve */
  font-size: 0.9rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(203, 166, 247, 0.15);
  /* Reduce background transparency */
  backdrop-filter: blur(4px);
  /* Reduce blur effect */
  border: 1px solid rgba(203, 166, 247, 0.3);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.5);
  /* Reduce text shadow */
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  /* Reduce shadow */
  z-index: 6;
}

/* Responsive text and element sizing */
@media (max-width: 768px) {
  .name {
    font-size: 1.1rem;
  }

  .works {
    font-size: 0.8rem;
    padding: 4px 8px;
    bottom: 8px;
    right: 8px;
  }

  .url-button-container {
    top: 8px;
    left: 8px;
  }

  .info-section {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .info-section {
    padding: 12px;
  }

  .url-button-container {
    top: 6px;
    left: 6px;
  }

  .name {
    font-size: 0.95rem;
  }

  .works {
    font-size: 0.75rem;
    padding: 4px 8px;
  }
}

/* Loading animation effect */
.card-item {
  animation: fadeInUp 0.6s ease-out forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
