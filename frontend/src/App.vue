<script setup>
import Header from "./components/Header.vue";
</script>
<template>
  <v-app>
    <Header />
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<style>
html,
body,
#app,
.v-application {
  width: 100vw;
  height: 100vh;
  min-height: 100vh;
  background: var(--color-base) !important; /* Catppuccin Mocha Base */
  margin: 0;
  padding: 0;
}

.v-main {
  background: var(--color-base) !important; /* Catppuccin Mocha Base */
  padding-top: 70px; /* Header height */
}

body {
  background: var(--color-base) !important; /* Catppuccin Mocha Base */
}

/* Override Vuetify default styles */
.v-application .primary {
  background-color: var(--color-blue) !important; /* Catppuccin Mocha Blue */
}

.v-application .secondary {
  background-color: var(--color-mauve) !important; /* Catppuccin Mocha Mauve */
}

/* Scrollbar styles */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: var(--color-surface-0); /* Catppuccin Mocha Surface0 */
}

::-webkit-scrollbar-thumb {
  background: var(--color-surface-2); /* Catppuccin Mocha Surface2 */
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-overlay); /* Catppuccin Mocha Overlay0 */
}
</style>
