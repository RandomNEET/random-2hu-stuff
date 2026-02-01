import { createRouter, createWebHistory } from "vue-router";

// Use lazy loading to reduce initial bundle size
const HomeView = () => import("../views/HomeView.vue");
const VideoView = () => import("../views/VideoView.vue");
const SearchView = () => import("../views/SearchView.vue");
const AboutView = () => import("../views/AboutView.vue");
const AnnounceView = () => import("../views/AnnounceView.vue");

const routes = [
  { path: "/", component: HomeView },
  { path: "/author/:id", component: VideoView, props: true },
  { path: "/search", component: SearchView },
  { path: "/announce", component: AnnounceView },
  { path: "/about", component: AboutView },
];

const router = createRouter({
  history: createWebHistory(), // Use history mode (recommended)
  routes,
});

export default router;
