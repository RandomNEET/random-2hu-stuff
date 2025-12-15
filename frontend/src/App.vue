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
  background: #1e1e2e !important; /* Catppuccin Mocha Base */
  margin: 0;
  padding: 0;
}

.v-main {
  background: #1e1e2e !important; /* Catppuccin Mocha Base */
  padding-top: 70px; /* Header height */
}

body {
  background: #1e1e2e !important; /* Catppuccin Mocha Base */
}

/* Override Vuetify default styles */
.v-application .primary {
  background-color: #89b4fa !important; /* Catppuccin Mocha Blue */
}

.v-application .secondary {
  background-color: #cba6f7 !important; /* Catppuccin Mocha Mauve */
}

/* Scrollbar styles */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #313244; /* Catppuccin Mocha Surface0 */
}

::-webkit-scrollbar-thumb {
  background: #585b70; /* Catppuccin Mocha Surface2 */
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #6c7086; /* Catppuccin Mocha Overlay0 */
}
</style>
