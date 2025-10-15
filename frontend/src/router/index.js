import { createRouter, createWebHistory } from "vue-router";

// Use lazy loading to reduce initial bundle size
const AuthorGrid = () => import("../components/AuthorGrid.vue");
const VideoList = () => import("../components/VideoList.vue");
const AboutView = () => import("../views/AboutView.vue");
const SearchView = () => import("../views/SearchView.vue");
const AnnouncementView = () => import("../views/AnnouncementView.vue");

const routes = [
  { path: "/", component: AuthorGrid },
  { path: "/author/:id", component: VideoList, props: true },
  { path: "/announcement", component: AnnouncementView },
  { path: "/about", component: AboutView },
  { path: "/search", component: SearchView },
];

const router = createRouter({
  history: createWebHistory(), // Use history mode (recommended)
  routes,
});

export default router;
