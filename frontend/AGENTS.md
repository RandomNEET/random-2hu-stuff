# 前端维护指南

适用于 `frontend/`，同时遵守 [根目录指南](../AGENTS.md)。这是 Vue 3 Composition API、JavaScript、Vuetify 和 Vite 应用；普通维护不引入 TypeScript 或更换状态、UI 框架。

## 从哪里修改

| 入口                                       | 职责                                                                           |
| ------------------------------------------ | ------------------------------------------------------------------------------ |
| `src/main.js`、`src/App.vue`               | 注册应用与全局布局                                                             |
| `src/router/index.js`                      | history 路由和懒加载页面                                                       |
| `src/views/`                               | 作者列表、作者视频、搜索、公告及关于页面                                       |
| `src/composables/`                         | 页面状态、watch、生命周期和浏览器事件                                          |
| `src/utils/`                               | 排序、筛选、视频分组、参数转换、格式化等纯逻辑                                 |
| `src/components/`                          | 按 layout、authors、videos、search、filters、common、about、widgets 分组的组件 |
| `src/services/api.js`、`src/config/api.js` | 请求与 API 地址配置                                                            |
| `src/data/announcements.js`                | 按新到旧排列的公告数据                                                         |
| `src/styles/`                              | 主题及跨组件共享样式                                                           |

新增逻辑先寻找相同职责的模块。页面状态分别由 `useAuthorsPage`、`useAuthorVideosPage`、`useSearchPage` 管理；不要在展示组件重复实现筛选和请求。

## 请求、URL 与状态

- 当前 API 基址写死在 `src/config/api.js`，默认指向线上。Vite 启动不会自动使用本地后端；联调时明确请求目标，不假定存在环境变量或代理切换。
- 作者链接查询直接展示后端身份匹配结果，不能再用名称文本过滤；无关键词时才加载完整作者列表，异步列表请求不得覆盖关键词搜索结果。普通名称查询保留本地过滤与作品数排序。
- `services/api.js` 返回原始 Response；HTTP 状态、错误与加载状态由调用方处理。维护时保留请求时序、失败处理及已有缓存行为。
- 保留 `/`、`/author/:id`、`/search`、`/announce`、`/about` 路由。移动页面文件时同步路由、测试和文档。
- `utils/searchQuery.js` 区分公开 URL 的 `status/from/to/minDur/maxDur/unknown` 与 API 的完整参数名；读取 URL 时短参数通过 `??` 优先于旧别名。不要直接把浏览器 query 当作后端参数。
- 修改持久化及参数恢复时，检查 composables 中全部 localStorage 键、默认值、URL 优先级、刷新及前进后退。不能因为两个页面实现相似就统一其状态规则。
- `AppHeader` 创建唯一搜索状态，并通过 `headerSearchContext` 提供给桌面、移动端和共享过滤组件。拆组件或切换断点时不能重复初始化、请求或丢失表单。

## 视频与展示行为

- 作者视频页和搜索页的标题处理、locale 优先级及同值排序存在差别。修改 `selectAuthorVideos.js`、`selectSearchVideos.js` 时分别检查预期，不强行合并。
- `groupVideosByName` 虽以 Name 命名，实际按链接分组：保留输入顺序，先尝试相同原视频 URL，再尝试相同转载 URL；首条记录决定分组备注和部分展示数据。不要改成按标题分组或合并为传递闭包。
- `VideoCard` 有地址时渲染原生链接。保留复制、中键、Ctrl/Cmd 等修饰点击，以及普通点击时既有桌面和移动端策略；无链接与原视频删除提示也需保留。
- `useBilibiliAvailability` 对转载卡片进行 JSONP 检查；保留回调唯一性、超时、script 和全局回调的卸载清理。请求失败与明确失效不是同一结果。
- 翻译状态标签、排序和筛选分别检查实际实现；不把空值或未知状态自动改成“暂无翻译”。
- `ListPagination` 通过 `appearance` 保留作者与视频列表的样式差别。共享模板不意味着强制统一布局。
- 公告 `items` 的每项代表一个列表项，内部为有序文本或链接段；`heading` 支持文本和换行段。修改时同步仓库外层 `update/scripts/updatelog.py` 及对应测试，保留文字、链接、顺序和影响布局的空格。

## 样式与验证

- 提取组件时一起检查 scoped CSS、父子 DOM、选择器优先级、声明顺序及响应式断点。将组件拥有的样式一起移动，确认父组件样式仍生效。
- 验证命令在仓库根目录执行：`npm --prefix test test`、`npm --prefix frontend run build`。交互或组件边界修改另运行 `npm run test:e2e`，布局、样式和 DOM 修改另运行 `npm run test:visual`。
- 所有测试与工具依赖在 `test/`；本目录的测试命令仅作转发。环境、浏览器及本地截图基线说明见 [测试文档](../test/README.md) 和 [测试指南](../test/AGENTS.md)。
- `test/frontend/fixtures/legacy-logic.js` 是冻结参照；不跟随重构修改它来消除差异。
