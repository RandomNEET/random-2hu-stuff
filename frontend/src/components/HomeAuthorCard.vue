<template>
  <a class="card-item" :href="'/author/' + author.id" target="_blank">
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
    <AuthorExternalLinkButton :author="author" />

    <!-- Info section in center -->
    <div class="info-section">
      <div class="name">{{ getDisplayName(author) }}</div>
    </div>

    <!-- Video count in bottom-right corner -->
    <div class="works">📊 {{ author.worksCount }} 视频</div>
  </a>
</template>

<script setup>
import AuthorExternalLinkButton from "./AuthorExternalLinkButton.vue";

const props = defineProps({
  author: {
    type: Object,
    required: true,
  },
});

// Helper function to get display name based on priority
const getDisplayName = (author) => {
  return author.yt_name || author.nico_name || author.twitter_name || "Unknown";
};

// Helper function to get display avatar based on priority
const getDisplayAvatar = (author) => {
  return author.nico_avatar || author.yt_avatar || author.twitter_avatar;
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
  text-decoration: none;
  color: inherit;
  display: block;
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

  .info-section {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .info-section {
    padding: 12px;
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