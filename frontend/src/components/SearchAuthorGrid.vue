<template>
  <div class="authors-grid">
    <v-card
      v-for="author in authors"
      :key="author.id"
      class="author-card"
      elevation="3"
      hover
      @click="$router.push(`/author/${author.id}`)"
    >
      <v-img :src="getDisplayAvatar(author)" class="author-avatar" />
      <div class="author-info">
        <div class="author-name">{{ getDisplayName(author) }}</div>
        <div class="author-works">视频数：{{ author.worksCount }}</div>
      </div>
    </v-card>
  </div>
</template>

<script setup>
const props = defineProps({
  authors: {
    type: Array,
    required: true
  }
});

const getDisplayName = (author) => {
  if (!author) return "Unknown";
  return author.yt_name || author.nico_name || author.twitter_name || "Unknown";
};

const getDisplayAvatar = (author) => {
  if (!author) return null;
  return author.nico_avatar || author.yt_avatar || author.twitter_avatar;
};
</script>

<style scoped>
.authors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 24px;
}

.author-card {
  background: #45475a !important; /* Catppuccin Mocha Surface1 */
  border: 1px solid #585b70; /* Catppuccin Mocha Surface2 */
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.author-card:hover {
  background: #585b70 !important; /* Catppuccin Mocha Surface2 */
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(203, 166, 247, 0.15);
}

.author-avatar {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  flex-shrink: 0;
}

.author-avatar :deep(.v-img__img) {
  object-fit: cover !important;
  width: 100% !important;
  height: 100% !important;
}

.author-info {
  padding: 16px;
  text-align: center;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.author-name {
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  font-size: 1.1rem;
  font-weight: bold;
  margin-bottom: 8px;
}

.author-works {
  color: #cba6f7; /* Catppuccin Mocha Mauve */
  font-size: 0.9rem;
}

/* Responsive design */
@media (max-width: 834px) {
  .authors-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
  }
}
</style>
