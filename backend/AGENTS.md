# 后端维护指南

适用于 `backend/`，同时遵守 [根目录指南](../AGENTS.md)。后端使用 CommonJS、Express 5、sqlite3 与 Fuse.js；API 进程只读，不承接数据导入或维护。

## 模块与启动

| 模块                     | 职责                                                            |
| ------------------------ | --------------------------------------------------------------- |
| `server.cjs`             | 打开数据库、监听端口、注册退出和启动失败处理                    |
| `src/app.cjs`            | `createApp` 注入 repository，注册路由、CORS、响应缓存与错误响应 |
| `src/database.cjs`       | 只读连接与 Promise 查询封装，创建 repository                    |
| `src/queries.cjs`        | 作者、视频、搜索快照和统计 SQL                                  |
| `src/search.cjs`         | query 解析、过滤、完整数据快照与 Fuse 索引复用                  |
| `src/search-links.cjs`   | 视频编号、视频与作者链接规范化及本地身份索引                    |
| `src/search-options.cjs` | Fuse 权重、阈值及翻译状态文案                                   |
| `src/cache.cjs`          | TTL、LRU、容量预算及并发加载合并                                |
| `ecosystem.config.js`    | PM2 进程配置，默认名 `r2s-api`                                  |

根目录执行 `node backend/server.cjs`。默认数据库为本目录的 `random-2hu-stuff.db`，可用 `DATABASE_PATH` 指定已有文件；端口由 `PORT` 指定，默认 3000。导入模块不应自行启动服务，测试优先使用 `createApp` 的注入接口及返回的 `close()` 清理定时器。

## 数据库与查询语义

- 使用 `OPEN_READONLY`。不存在的数据库必须启动失败，不创建空库，不在启动时迁移、建索引、VACUUM、ANALYZE 或修改持久化 PRAGMA。当前 cache_size、temp_store 仅设置连接内存。
- 作者作品数先按 author 聚合再连接作者；不要为聚合对宽作者记录做不必要的分组。
- 作者平均时长：同一作者的相同非空原链接为一个样本，优先取最大原时长，全未知才取最大转载时长；没有原链接的记录各自成为样本。保留 0、NULL、空字符串和空白字符串的区别。
- 全站作者数包含无作品作者；视频数、已翻译数及最大时长只计可关联作者的视频。已翻译只计状态 1、2。最大时长使用原时长优先、转载时长回退。
- 作者视频查询保留日期及 id 升序；搜索快照也有确定顺序。修改 SQL 时对照测试，不能依赖 SQLite 偶然返回顺序。

## 接口与缓存

- 路由以 `src/app.cjs` 为准：作者列表、单作者视频、筛选用作者列表、统计、视频及作者搜索，以及 `/health`。前端配置的 `/api/videos` 当前没有对应路由。
- 搜索无 q 时返回既有 400 JSON；加载失败保留 500 JSON 及搜索错误前缀。`/health` 保持 `status`、`timestamp`、`cacheSize`，不要把它扩展解释成数据库实时探针。
- 保留 query 的解析边界：时长允许 0，非有限数和负时长无效；未知时长由 `includeUnknownDuration === "1"` 控制。limit 的默认、上限及负数 slice 兼容行为不能在重构中顺带修正。
- 完整链接与视频编号通过 `search-links.cjs` 精确匹配，AV/BV 本地互通；身份索引在首次链接查询时建立，随完整快照刷新。链接结果继续应用筛选和 limit，按快照顺序返回，分数为 0；普通关键词保持 Fuse 行为。不联网解析短链或推断 YouTube 频道别名。
- 视频先过滤再模糊搜索，时长用 `original_duration ?? repost_duration`；保留 Fuse 分数、权重、排序、输出字段及未知状态“未知”文案。
- 响应缓存保存 JSON 字符串，默认 TTL 5 分钟，最多 256 项、32 MiB UTF-8 字节预算；命中不重复序列化。同键并发未命中共享 Promise，失败不得缓存，淘汰同时维护权重。
- 搜索快照中的视频和作者必须全部加载成功后一起发布；失败清除 refreshing 状态以便重试。快照也有独立的 5 分钟 TTL，不能声称两层缓存等于端到端最多 5 分钟延迟。
- Fuse 索引按快照和筛选条件复用，不随搜索词或 limit 重建。筛选集合缓存最多 32 项、累计记录预算为完整视频数的两倍，空集合也受容量限制。
- JSON Content-Type、ETag、条件请求和 CORS 仍由 Express 处理；优化响应路径时检查这些兼容行为。

## 验证及打包

根目录安装 `backend/` 和 `test/` 依赖后执行 `npm run test:backend`；性能相关改动另运行 `npm run bench:backend`。测试位于 `test/backend/`，使用内存或临时 SQLite，不使用业务数据库。

`test/backend/fixtures/legacy-server.cjs` 是冻结参照，只通过 `legacy.cjs` 的沙箱执行。性能对照用合成数据检查结果和索引构建次数，计时不代表线上性能。

增加运行时模块时检查 `deploy/deploy.sh` 与 `update/scripts/upload.sh` 的复制清单。运行包需要 `server.cjs` 和完整 `src/`；不实际部署或上传数据库验证打包。
