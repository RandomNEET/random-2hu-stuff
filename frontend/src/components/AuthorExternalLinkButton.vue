<template>
  <div v-if="getDisplayUrl(author)" class="url-button-container">
    <v-btn
      icon
      size="small"
      class="url-button"
      @click.stop.prevent="handleUrlClick"
      :title="primaryTitle"
    >
      <v-icon size="16">mdi-open-in-new</v-icon>
    </v-btn>

    <div v-if="hasMultipleUrls(author) && isExpanded" class="platform-buttons">
      <v-btn
        v-if="author.yt_url"
        icon
        size="small"
        class="platform-btn youtube-btn"
        @click.stop.prevent="openSpecificUrl(author.yt_url)"
        title="YouTube频道"
      >
        <v-icon size="14">mdi-youtube</v-icon>
      </v-btn>
      <v-btn
        v-if="author.nico_url"
        icon
        size="small"
        class="platform-btn nico-btn"
        @click.stop.prevent="openSpecificUrl(author.nico_url)"
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
        @click.stop.prevent="openSpecificUrl(author.twitter_url)"
        title="Twitter频道"
      >
        <v-icon size="14">mdi-twitter</v-icon>
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  author: {
    type: Object,
    required: true,
  },
});

const isExpanded = ref(false);

// Helper function to get display URL based on priority
const getDisplayUrl = (author) => {
  return author.yt_url || author.nico_url || author.twitter_url;
};

// Check if author has multiple URLs
const hasMultipleUrls = (author) => {
  if (!author) return false;
  const urlCount = [author.yt_url, author.nico_url, author.twitter_url].filter(
    Boolean,
  ).length;
  return urlCount > 1;
};

const primaryTitle = computed(() => {
  if (!props.author) return "访问作者频道";
  if (hasMultipleUrls(props.author)) return "展开频道列表";
  if (props.author.yt_url) return "访问YouTube频道";
  if (props.author.nico_url) return "访问NicoNico频道";
  if (props.author.twitter_url) return "访问Twitter频道";
  return "访问作者频道";
});

// Handle URL button click - direct navigation if only one URL,
// otherwise toggle expand to show platform buttons
const handleUrlClick = () => {
  if (!hasMultipleUrls(props.author)) {
    const url = getDisplayUrl(props.author);
    if (url) {
      openUrl(url);
    }
  } else {
    isExpanded.value = !isExpanded.value;
  }
};

// Open specific URL (YouTube / NicoNico / Twitter)
const openSpecificUrl = (url) => {
  if (url) {
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
    isExpanded.value = false;
  }
};

const openUrl = (url) => {
  if (url) {
    const fullUrl = url.startsWith("http") ? url : `https://${url}`;
    window.open(fullUrl, "_blank", "noopener,noreferrer");
  }
};

// Collapse the platform buttons when clicking anywhere outside the container
const handleClickOutside = (event) => {
  if (isExpanded.value && !event.target.closest(".url-button-container")) {
    isExpanded.value = false;
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<style scoped>
.url-button-container {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.url-button {
  background-color: rgba(30, 30, 46, 0.9) !important;
  color: #89b4fa !important; /* Catppuccin Mocha Blue */
  transition: all 0.3s ease;
  backdrop-filter: blur(12px);
  border: 2px solid rgba(137, 180, 250, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.url-button:hover {
  background-color: rgba(137, 180, 250, 0.2) !important;
  color: #74c7ec !important; /* Catppuccin Mocha Sapphire */
  transform: scale(1.15);
  border-color: rgba(116, 199, 236, 0.6);
  box-shadow: 0 4px 20px rgba(137, 180, 250, 0.5);
}

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

@media (max-width: 480px) {
  .url-button-container {
    top: 6px;
    left: 6px;
  }
}
</style>
