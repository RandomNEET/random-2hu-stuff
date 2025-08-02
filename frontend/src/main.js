import { createApp } from "vue";
import router from "./router";

// Vuetify
import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";

// Material Design Icons
import "@mdi/font/css/materialdesignicons.css";

// Components
import App from "./App.vue";

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "dark",
  },
});

const app = createApp(App);
app.use(router);
app.use(vuetify);
app.mount("#app");
