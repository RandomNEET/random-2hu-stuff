<template>
  <v-app-bar
    app
    elevation="4"
    class="app-header"
    height="70"
  >
    <v-container class="d-flex align-center">
      <!-- Site title -->
      <div class="site-title" @click="$router.push('/')" style="cursor: pointer">
        <h1 class="title-text">random 2hu stuff</h1>
      </div>

      <v-spacer></v-spacer>

      <!-- Desktop search bar -->
      <div class="search-container">
        <v-text-field
          v-model="searchQuery"
          placeholder="搜索作者或视频..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          hide-details
          class="search-field desktop-search"
          @keyup.enter="handleSearch"
        />
      </div>

      <v-spacer></v-spacer>

      <!-- Navigation menu -->
      <div class="nav-menu">
        <!-- Mobile search toggle button -->
        <v-btn
          icon
          class="mobile-search-btn"
          @click="showMobileSearch = !showMobileSearch"
        >
          <v-icon>mdi-magnify</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/')"
        >
          <v-icon>mdi-home</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/announcement')"
        >
          <v-icon>mdi-bullhorn</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/about')"
        >
          <v-icon>mdi-information</v-icon>
        </v-btn>
      </div>
    </v-container>

    <!-- Mobile search popup overlay -->
    <div v-if="showMobileSearch" class="mobile-search-overlay" @click="showMobileSearch = false">
      <div class="mobile-search-popup" @click.stop>
        <v-text-field
          v-model="searchQuery"
          placeholder="搜索作者或视频..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          hide-details
          class="search-field mobile-popup-search"
          @keyup.enter="handleMobileSearch"
          autofocus
        />
        <v-btn
          icon
          class="close-btn"
          @click="showMobileSearch = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </div>
    </div>
  </v-app-bar>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const searchQuery = ref('');
const showMobileSearch = ref(false);

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    // Navigate to search results page with query parameter
    router.push({
      path: '/search',
      query: { q: searchQuery.value.trim() }
    });
  }
};

const handleMobileSearch = () => {
  if (searchQuery.value.trim()) {
    // Navigate to search results page with query parameter
    router.push({
      path: '/search',
      query: { q: searchQuery.value.trim() }
    });
    showMobileSearch.value = false; // Close the popup overlay
  }
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* Header with Catppuccin Mocha theme */
.app-header {
  background: linear-gradient(135deg, #1e1e2e 0%, #313244 100%) !important; /* Catppuccin Mocha gradient */
  border-bottom: 2px solid #45475a; /* Catppuccin Mocha Surface1 */
  font-family: 'JetBrains Mono', 'JetBrainsMono Nerd Font', monospace !important;
}

.app-header * {
  font-family: 'JetBrains Mono', 'JetBrainsMono Nerd Font', monospace !important;
}

.site-title {
  transition: transform 0.2s ease;
  flex-shrink: 0; /* Prevent title from being compressed */
}

.site-title:hover {
  transform: scale(1.05);
}

.title-text {
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.search-container {
  max-width: 400px;
  width: 100%;
}

.mobile-search-container {
  display: none; /* Hidden by default for mobile search */
  width: 100px;
  margin-right: 8px;
}

.mobile-search-btn {
  display: none; /* Hidden by default for mobile search button */
  color: #cdd6f4 !important;
  transition: all 0.2s ease;
  border: 1px solid #585b70 !important; /* Add border for normal state */
}

.mobile-search-btn:hover {
  background-color: rgba(137, 180, 250, 0.1) !important;
  color: #89b4fa !important;
  border-color: #89b4fa !important; /* Change border color on hover */
}

.desktop-search {
  display: block; /* Show desktop search by default */
}

.mobile-search {
  display: none; /* Hide mobile search by default */
}

.search-field :deep(.v-field) {
  background-color: #45475a !important; /* Catppuccin Mocha Surface1 */
  border-radius: 12px;
}

.search-field :deep(.v-field__input) {
  color: #cdd6f4 !important; /* Catppuccin Mocha Text */
}

.search-field :deep(.v-field__outline) {
  border-color: #585b70 !important; /* Catppuccin Mocha Surface2 */
}

.search-field :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important; /* Catppuccin Mocha Blue */
}

.search-field :deep(.v-field__prepend-inner .v-icon) {
  color: #a6adc8 !important; /* Catppuccin Mocha Subtext0 */
}

.search-field :deep(::placeholder) {
  color: #6c7086 !important; /* Catppuccin Mocha Overlay0 */
}

.nav-menu {
  display: flex;
  gap: 8px;
  flex-shrink: 0; /* Prevent compression on small screens */
  align-items: center; /* Ensure buttons are vertically centered */
}

.nav-button {
  color: #cdd6f4 !important; /* Catppuccin Mocha Text */
  transition: all 0.2s ease;
  border: 1px solid #585b70 !important; /* Add border for normal state */
}

.nav-button:hover {
  background-color: rgba(137, 180, 250, 0.1) !important; /* Catppuccin Mocha Blue with opacity */
  color: #89b4fa !important; /* Catppuccin Mocha Blue */
  border-color: #89b4fa !important; /* Change border color on hover */
}

/* Mobile search popup overlay styles */
.mobile-search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 2000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px; /* Leave space for header */
}

.mobile-search-popup {
  background: #1e1e2e;
  border-radius: 16px;
  padding: 20px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border: 1px solid #45475a;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-popup-search {
  flex: 1;
}

.close-btn {
  color: #cdd6f4 !important;
  flex-shrink: 0;
}

.close-btn:hover {
  background-color: rgba(243, 139, 168, 0.1) !important;
  color: #f38ba8 !important;
}

/* Responsive design */
@media (max-width: 960px) {
  .title-text {
    font-size: 1.2rem;
  }
  
  .search-container {
    display: none; /* Hide desktop search bar */
  }
  
  .desktop-search {
    display: none !important; /* Hide desktop search */
  }
  
  .mobile-search-btn {
    display: flex !important; /* Show mobile search button */
  }
}

@media (max-width: 600px) {
  .app-header :deep(.v-container) {
    padding: 0 12px !important; /* Appropriate padding for mobile */
  }
  
  .title-text {
    font-size: 1rem;
  }
  
  .nav-menu {
    gap: 4px; /* Reduce button spacing */
  }
  
  .nav-button {
    width: 40px !important; /* Set fixed width */
    height: 40px !important; /* Set fixed height to maintain circular shape */
    min-width: 40px !important; /* Minimum width */
  }
  
  .mobile-search-btn {
    width: 40px !important; /* Set fixed width */
    height: 40px !important; /* Set fixed height to maintain circular shape */
    min-width: 40px !important;
  }
  
  .mobile-search-popup {
    width: 95%;
    padding: 16px;
  }
}
</style>
