# 仓库维护指南

本文件适用于整个仓库。修改子目录前阅读就近的 `AGENTS.md`；前端、后端、数据更新、更新脚本、自动抓取、部署及测试均有对应指南。以当前代码、配置和测试确认具体行为；本文件记录维护边界和入口，不记录任务进度。

## 项目与代码入口

这是东方视频作者及原视频、转载视频的索引站。前端负责作者浏览、视频分组、搜索筛选和公告展示，后端提供只读查询；数据采集、导入及维护由独立 Python 和 Shell 工具完成。

| 路径                                            | 实际职责与入口                                                                                                                                     |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend/src/`                                 | Vue 3 Composition API、JavaScript、Vuetify；`main.js` 启动，`router/index.js` 定义路由，Vite 构建                                                  |
| `frontend/src/views/`、`components/`            | 页面与展示组件；页面状态在 `composables/`，纯数据处理在 `utils/`                                                                                   |
| `frontend/src/services/api.js`、`config/api.js` | fetch 请求封装与 API 地址；服务层返回原始 Response                                                                                                 |
| `backend/server.cjs`                            | Node CommonJS 服务入口；连接 SQLite 后启动 Express，处理退出                                                                                       |
| `backend/src/`                                  | `app.cjs` 定义路由，`database.cjs` 封装只读连接，`queries.cjs` 定义 SQL，`search.cjs` 与 `search-options.cjs` 管理 Fuse 搜索，`cache.cjs` 管理缓存 |
| `update/scripts/`                               | CSV 导入、作者和视频元数据维护、查重、导出、公告生成与上传                                                                                         |
| `update/autofetch/`                             | `fetcher.py` 抓取 RSS，`processor.py` 处理视频信息，`upload.py` 整理及上传表格；配置在 `config/*.jsonc`                                            |
| `deploy/`                                       | Debian 代码部署、数据库获取和替换、Nginx 配置；直接阅读对应脚本确认参数及前置条件                                                                  |
| `test/`                                         | 前后端、更新工具及部署测试，测试依赖、夹具、配置和本地产物；操作说明见 [测试文档](test/README.md)                                                  |
| `flake.nix`                                     | Nix 开发环境与格式化工具配置；开发 shell 设置 `PROJECT_ROOT`                                                                                       |

收录规则、表格列含义和人工维护流程见 [数据维护说明](update/readme.md)，工具边界见 [更新指南](update/AGENTS.md)、[脚本指南](update/scripts/AGENTS.md) 和 [自动抓取指南](update/autofetch/AGENTS.md)。实现调整不得自行改写这些业务规则。

## 工作方式

- 先检查 `git status`、目标实现、调用方和相关测试；保留用户已有的改动，不清理无关文件。
- 按任务范围完成实现及必要验证。未要求时不提交、推送、上传或部署。
- 普通维护及重构保持既有界面、数据格式、URL、排序和失败处理，不混入框架迁移、依赖升级或全仓格式化。
- 修改字段、模块名、路径或命令后，用仓库级搜索检查调用方、更新脚本、打包清单、测试及文档。抽象应承载真实的共享职责。
- 长期架构或维护入口发生变化时更新对应指南；具体操作尽量引用已有文档或脚本，避免复制多份说明。

## 本地运行与路径

依赖分别安装在三个目录，根目录不统一安装这些依赖。以下命令在仓库根目录执行：

```sh
npm --prefix frontend ci
npm --prefix backend ci
npm --prefix test ci
npm --prefix frontend run dev
# 在另一个终端启动 API，需要已有且结构正确的数据库：
node backend/server.cjs
```

- 后端默认打开 `backend/random-2hu-stuff.db`，支持 `DATABASE_PATH` 和 `PORT`，默认端口为 3000。数据库以只读方式打开，不存在时启动失败。
- 前端 API 基址写在 `frontend/src/config/api.js`，当前默认指向线上站点。启动本地 Vite 或后端不会自动切换 API；联调前先确认请求目标。
- 前端使用 history 路由：`/`、`/author/:id`、`/search`、`/announce`、`/about`。部署需支持页面路径回退，同时保留 API、健康检查及缺失静态资源的独立处理。
- 可通过 `nix develop` 使用 `flake.nix` 中的 Node、Python、SQLite、Dolt 等工具；Python 环境包含 requests、yt-dlp、openpyxl、json5。不要假定 `npm ci` 会安装 Python 依赖或浏览器。
- 更新工具的路径解析并不统一：有的使用 `PROJECT_ROOT`，有的相对脚本位置或当前目录定位。运行前阅读具体实现，确认数据库、CSV、配置和输出位置；不要把所有脚本都当成可从任意目录运行。

## 数据和接口契约

- 核心表为 `authors` 与 `videos`，`videos.author` 关联 `authors.id`。作者包含 YouTube、Niconico、Twitter 的名称、链接、头像及备注；视频分别保存原视频与转载视频的标题、链接、缩略图、时长，以及日期、翻译状态和备注。
- 翻译状态为 `1` 中文内嵌、`2` CC 字幕、`3` 弹幕翻译、`4` 无需翻译、`5` 暂无翻译。保留未知值和空值在各调用方中的既有行为，不擅自统一映射或回退值。
- “作品数”、按原视频链接去重后的平均时长、全站视频数及已翻译数不是同一口径。当前全站已翻译数只计状态 1、2，视频数只计可关联到作者的记录；改动统计时同步检查 SQL、前端展示及 `updatelog.py`。
- 后端现有端点是 `/api/authors`、`/api/author/:id/videos`、`/api/authors/list`、`/api/stats`、`/api/search/videos`、`/api/search/authors` 和 `/health`。前端配置中存在的常量不一定代表已实现的路由，例如 `/api/videos`。
- 后端 API 不承担写入、迁移或数据库维护；查询、搜索过滤顺序、结果字段、错误格式和缓存行为的细节见后端指南。修改接口时同时检查前端服务与 composables。
- 前端 URL 参数及别名、localStorage 键、视频分组、链接点击和响应式共享搜索状态属于兼容行为。具体约束见前端指南，提取组件时连同样式作用域和生命周期一起检查。
- 公告由 `frontend/src/data/announcements.js` 提供，`update/scripts/updatelog.py` 插入新条目并更新 `update/scripts/content.log`。修改公告结构须同步渲染组件、生成脚本和公告测试，不向 Vue 模板插入生成 HTML。

## 数据维护与部署边界

操作约束见 [部署指南](deploy/AGENTS.md)，测试维护约束见 [测试指南](test/AGENTS.md)。

- 修改更新工具前检查输入格式、匹配和覆盖规则、数据库连接方式及副作用。部分脚本会写库、请求外部平台、读取 cookies 或上传在线表格；不得用真实导入、清理、抓取上传来代替回归测试。
- 使用固定夹具、内存库或临时数据库验证。即使脚本支持 `--dry-run`，也先确认实现是否仍连接数据库、请求网络或生成文件。
- `deploy/deploy.sh` 部署代码，依赖既有 Debian、Nginx 和 PM2 环境；默认目标为 `/var/www/random-2hu-stuff`，PM2 名为 `r2s-api`。它保留数据库与现有 Nginx 配置，前端复制保留旧哈希资源。修改时维持这些边界。
- `update/scripts/upload.sh` 默认会上传并执行部署，`upload-only` 只上传源码，`build-only` 本地构建，`database-only` 单独更新数据库。数据库上传使用 SQLite backup 获取包含 WAL 内容的一致快照，再调用 `deploy/replace-database.sh` 校验、备份、替换和失败恢复。
- `deploy/get-db.sh` 从 DoltHub 导出 SQLite，会删除既有输出文件再生成。不要作为普通启动或测试步骤执行。
- 后端新增或移动运行时文件时，同步检查部署与上传脚本的复制清单；当前运行包需要 `server.cjs`、完整 `src/`、依赖清单及 PM2 配置。
- 不将 `.env`、cookies、凭据、数据库、node_modules、构建及测试产物加入版本控制。保留 `.gitignore` 的明确例外：`backend/full-data.csv` 和 `update/scripts/content.log`。

## 按改动选择验证

以下命令均从仓库根目录运行，依赖需预先安装：

| 改动范围                  | 验证入口                                                     |
| ------------------------- | ------------------------------------------------------------ |
| 前端纯逻辑、composables   | `npm --prefix test test`                                     |
| 前端生产构建              | `npm --prefix frontend run build`                            |
| 后端查询、API、搜索或缓存 | `npm run test:backend`                                       |
| 后端性能相关改动          | `npm run bench:backend`，使用合成内存数据并核对结果一致性    |
| 更新工具                  | `npm run test:python`，或选择 `test/update/` 中相关 unittest |
| 部署、上传或 Nginx 配置   | `npm run test:deploy`                                        |
| 用户交互或组件边界        | `npm run test:e2e`                                           |
| 布局、样式或 DOM          | `npm run test:visual`                                        |
| 综合回归                  | `npm test`，包括前端单元、后端、更新工具 Python 和部署测试   |

- 测试实现、夹具、配置及测试专用依赖统一放在 `test/`；不要散落回生产目录。根目录和前端的测试命令可作为转发入口。
- 后端测试使用内存或临时数据库，接口测试需要本地临时端口；部署测试使用临时目录和模拟服务命令，需要 rsync。Nginx 集成测试可用 `NGINX_BIN` 指定二进制，缺少时会跳过；报告时区分通过与跳过。
- 浏览器测试由 Playwright 启动 Vite，并使用固定 API 夹具。首次运行可执行 `npm --prefix test exec -- playwright install chromium`，或用 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 指定已有浏览器。
- 截图覆盖 390、768、834、1440 像素宽度。基线仅存本地且被 Git 忽略；新检出仓库应在认可的代码版本先建立基线，再修改并比较。不能在改动后直接更新基线来证明外观未变。
- `test/frontend/fixtures/legacy-logic.js` 与 `test/backend/fixtures/legacy-server.cjs` 是冻结行为参照，不随实现修改来消除差异；后者只通过 `legacy.cjs` 的沙箱使用。
- 纯文档修改核对路径、命令和 diff 即可。交付时说明修改结果、实际执行的验证及未验证项；不把环境缺失、测试跳过或合成数据计时表述成完整验证或线上性能保证。
