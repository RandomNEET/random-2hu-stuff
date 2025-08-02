import { createRouter, createWebHistory } from "vue-router";

// 你的页面组件（根据自己的实际路径调整）
import AuthorGrid from "../components/AuthorGrid.vue";
import VideoList from "../components/VideoList.vue";
import AboutView from "../views/AboutView.vue";
import SearchView from "../views/SearchView.vue";
import AnnouncementView from "../views/AnnouncementView.vue";

const routes = [
  { path: "/", component: AuthorGrid },
  { path: "/author/:name", component: VideoList, props: true },
  { path: "/announcement", component: AnnouncementView },
  { path: "/about", component: AboutView },
  { path: "/search", component: SearchView },
];

const router = createRouter({
  history: createWebHistory(), // 使用history模式（推荐）
  routes,
});

export default router;
