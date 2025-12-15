import { createRouter, createWebHistory } from "vue-router";

// Use lazy loading to reduce initial bundle size
const AuthorGrid = () => import("../pages/AuthorGrid.vue");
const VideoList = () => import("../pages/VideoList.vue");
const About = () => import("../pages/About.vue");
const Search = () => import("../pages/Search.vue");
const Announcement = () => import("../pages/Announcement.vue");

const routes = [
  { path: "/", component: AuthorGrid },
  { path: "/author/:id", component: VideoList, props: true },
  { path: "/announcement", component: Announcement },
  { path: "/about", component: About },
  { path: "/search", component: Search },
];

const router = createRouter({
  history: createWebHistory(), // Use history mode (recommended)
  routes,
});

export default router;
