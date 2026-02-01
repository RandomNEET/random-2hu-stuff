<template>
  <div class="author-header" v-if="author">
    <div
      class="author-avatar"
      v-if="displayAvatar"
      :class="{ 'avatar-hidden': !showAvatar }"
    >
      <img
        :src="displayAvatar"
        :alt="displayName"
        @load="handleAvatarLoad"
        @error="handleAvatarError"
      />
    </div>
    <div class="author-info">
      <h1 class="author-name">{{ displayName }}</h1>
      <div v-if="author.comment" class="author-comment" v-html="processedComment"></div>
      <div class="video-count">📊 {{ videoCount }} 个视频</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  author: {
    type: Object,
    default: null
  },
  videoCount: {
    type: Number,
    default: 0
  }
});

const avatarLoaded = ref(false);
const showAvatar = ref(false);
let loadingTimeout = null;

// Helper function to get display name based on priority
const displayName = computed(() => {
  if (!props.author) return "Unknown";
  return props.author.yt_name || props.author.nico_name || props.author.twitter_name || "Unknown";
});

// Helper function to get display avatar based on priority
const displayAvatar = computed(() => {
  if (!props.author) return null;
  return props.author.nico_avatar || props.author.yt_avatar || props.author.twitter_avatar;
});

// Process comment text to make URLs clickable
const processedComment = computed(() => {
  if (!props.author?.comment) return '';
  
  // Escape HTML first to prevent XSS
  const escapeHtml = (text) => {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  };
  
  // Escape the comment first
  let processedComment = escapeHtml(props.author.comment);
  
  // Regular expression to match URLs (http, https, and domain-only)
  const urlRegex = /(https?:\/\/[^\s]+|(?:(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^\s]*)?))(?=\s|$|[,.!?;)])/g;
  
  // Replace URLs with clickable links
  processedComment = processedComment.replace(urlRegex, (url) => {
    // Ensure URL has protocol
    const fullUrl = url.startsWith('http') ? url : `https://${url}`;
    return `<a href="${fullUrl}" target="_blank" rel="noopener noreferrer" class="comment-link">${url}</a>`;
  });
  
  return processedComment;
});

// Avatar loading handler functions
const handleAvatarLoad = () => {
  avatarLoaded.value = true;
  showAvatar.value = true;
  if (loadingTimeout) {
    clearTimeout(loadingTimeout);
    loadingTimeout = null;
  }
};

const handleAvatarError = () => {
  avatarLoaded.value = false;
  showAvatar.value = false;
  if (loadingTimeout) {
    clearTimeout(loadingTimeout);
    loadingTimeout = null;
  }
};

onMounted(() => {
  // Set timeout to hide avatar if it doesn't load within 5 seconds
  if (displayAvatar.value) {
    loadingTimeout = setTimeout(() => {
      if (!avatarLoaded.value) {
        showAvatar.value = false;
      }
      loadingTimeout = null;
    }, 5000);
  }
});

onUnmounted(() => {
  if (loadingTimeout) {
    clearTimeout(loadingTimeout);
    loadingTimeout = null;
  }
});
</script>

<style scoped>
/* Author information header */
.author-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 32px;
  background: linear-gradient(135deg, #313244 0%, #45475a 100%);
  border-bottom: 2px solid #585b70;
}

.author-avatar {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  transition: opacity 0.3s ease, width 0.3s ease, height 0.3s ease;
}

.author-avatar.avatar-hidden {
  opacity: 0;
  visibility: hidden;
  width: 0;
  height: 0;
  min-width: 0;
  min-height: 0;
  box-shadow: none;
}

.author-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-info {
  flex: 1;
}

.author-name {
  font-size: 2rem;
  font-weight: bold;
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  margin: 0 0 8px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.video-count {
  font-size: 1.1rem;
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  background: rgba(203, 166, 247, 0.1);
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-block;
  border: 1px solid rgba(203, 166, 247, 0.3);
  margin-bottom: 8px;
}

.author-comment {
  font-size: 1rem;
  color: #a6adc8; /* Catppuccin Mocha Subtext0 */
  padding: 4px 0;
  margin-bottom: 12px;
  line-height: 1.4;
}

.author-comment :deep(.comment-link) {
  color: #89b4fa; /* Catppuccin Mocha Blue */
  text-decoration: underline;
  transition: color 0.2s ease;
}

.author-comment :deep(.comment-link:hover) {
  color: #74c7ec; /* Catppuccin Mocha Sapphire */
  text-decoration: underline;
}

/* Responsive design */
@media (max-width: 834px) {
  .author-header {
    padding: 24px 20px;
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }

  .author-avatar {
    width: 120px;
    height: 120px;
  }

  .author-name {
    font-size: 1.6rem;
  }
}

@media (max-width: 480px) {
  .author-header {
    padding: 20px 16px;
  }

  .author-avatar {
    width: 100px;
    height: 100px;
  }

  .author-name {
    font-size: 1.4rem;
  }

  .video-count {
    font-size: 1rem;
    padding: 4px 8px;
  }

  .author-comment {
    font-size: 0.9rem;
    padding: 2px 0;
    margin-bottom: 10px;
  }

  .author-comment :deep(.comment-link) {
    color: #89b4fa; /* Keep same link color on mobile */
  }
}
</style>
