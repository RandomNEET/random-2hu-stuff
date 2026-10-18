import { createRouter, createWebHistory } from "vue-router";

// Use lazy loading to reduce initial bundle size
const AuthorsView = () => import("../views/AuthorsView.vue");
const AuthorVideosView = () => import("../views/AuthorVideosView.vue");
const SearchView = () => import("../views/SearchView.vue");
const AboutView = () => import("../views/AboutView.vue");
const AnnouncementsView = () => import("../views/AnnouncementsView.vue");

const routes = [
  { path: "/", component: AuthorsView },
  { path: "/author/:id", component: AuthorVideosView, props: true },
  { path: "/search", component: SearchView },
  { path: "/announce", component: AnnouncementsView },
  { path: "/about", component: AboutView },
];

const router = createRouter({
  history: createWebHistory(), // Use history mode (recommended)
  routes,
});

export default router;
