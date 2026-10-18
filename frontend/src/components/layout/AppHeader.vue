<template>
  <v-app-bar app elevation="4" class="app-header" height="70">
    <v-container class="d-flex align-center">
      <!-- Site title -->
      <div
        class="site-title"
        @click="$router.push('/')"
        style="cursor: pointer"
      >
        <h1 class="title-text">random 2hu stuff</h1>
      </div>

      <v-spacer></v-spacer>

      <!-- Desktop search bar with dropdown -->
      <HeaderDesktopSearch />

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

        <v-btn icon class="nav-button" @click="$router.push('/')">
          <v-icon>mdi-home</v-icon>
        </v-btn>

        <v-btn icon class="nav-button" @click="$router.push('/announce')">
          <v-icon>mdi-bullhorn</v-icon>
        </v-btn>

        <v-btn icon class="nav-button" @click="$router.push('/about')">
          <v-icon>mdi-information</v-icon>
        </v-btn>
      </div>
    </v-container>

    <!-- Mobile search popup overlay -->
    <HeaderMobileSearch v-if="showMobileSearch" />
  </v-app-bar>
</template>

<script setup>
import HeaderDesktopSearch from "@/components/search/HeaderDesktopSearch.vue";
import HeaderMobileSearch from "@/components/search/HeaderMobileSearch.vue";
import { provideHeaderSearch } from "@/components/search/headerSearchContext.js";
import { useHeaderSearch } from "@/composables/useHeaderSearch.js";

const search = useHeaderSearch();
provideHeaderSearch(search);
const { showMobileSearch } = search;
</script>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap");
.app-header {
  background: linear-gradient(
    135deg,
    var(--color-base) 0%,
    var(--color-surface-0) 100%
  ) !important; /* Catppuccin Mocha gradient */
  border-bottom: 2px solid var(--color-surface-1); /* Catppuccin Mocha Surface1 */
  font-family:
    "JetBrains Mono", "JetBrainsMono Nerd Font", monospace !important;
}
.app-header :deep(*) {
  font-family:
    "JetBrains Mono", "JetBrainsMono Nerd Font", monospace !important;
}
.site-title {
  transition: transform 0.2s ease;
  flex-shrink: 0; /* Prevent title from being compressed */
}
.site-title:hover {
  transform: scale(1.05);
}
.title-text {
  color: var(--color-yellow); /* Catppuccin Mocha Yellow */
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 2px 4px var(--color-black-30);
}
.mobile-search-btn {
  display: none !important; /* Ensure hidden on desktop; override Vuetify */
  color: var(--color-text) !important;
  transition: all 0.2s ease;
  border: 1px solid var(--color-surface-2) !important; /* Add border for normal state */
  border-radius: 50% !important; /* Keep shape perfectly circular when shown */
}
.mobile-search-btn:hover {
  background-color: var(--color-blue-10) !important;
  color: var(--color-blue) !important;
  border-color: var(--color-blue) !important; /* Change border color on hover */
}
.nav-menu {
  display: flex;
  gap: 8px;
  flex-shrink: 0; /* Prevent compression on small screens */
  align-items: center; /* Ensure buttons are vertically centered */
}
.nav-button {
  color: var(--color-text) !important; /* Catppuccin Mocha Text */
  transition: all 0.2s ease;
  border: 1px solid var(--color-surface-2) !important; /* Add border for normal state */
}
.nav-button:hover {
  background-color: rgba(
    137,
    180,
    250,
    0.1
  ) !important; /* Catppuccin Mocha Blue with opacity */
  color: var(--color-blue) !important; /* Catppuccin Mocha Blue */
  border-color: var(--color-blue) !important; /* Change border color on hover */
}
@media (max-width: 960px) {
  .title-text {
    font-size: 1.2rem;
  }

  .mobile-search-btn {
    display: flex !important; /* Show mobile search button */
    width: 40px !important; /* Ensure square dimensions */
    height: 40px !important;
    min-width: 40px !important;
    border-radius: 50% !important; /* Guarantee circle across tablet widths */
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
}
</style>
