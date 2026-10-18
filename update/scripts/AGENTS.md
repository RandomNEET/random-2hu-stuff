# 导入和维护脚本指南

适用于本目录，同时遵守 [上级指南](../AGENTS.md)。维护前阅读目标脚本的参数解析、默认路径、连接方式和主流程，不假定同目录脚本具有统一 CLI 或事务策略。

## 工具分工

| 入口 | 职责及联动 |
| --- | --- |
| `csv-import.py`、`csv-cleaner.py` | 导入视频及清理输入 CSV；检查作者匹配、原/转载链接匹配、覆盖确认和表格列格式 |
| `metadata-updater.py` | 更新视频元数据；检查并发、ID 范围、失效链接状态与重试策略 |
| `update-author-info.py`、`author_links.py` | 作者名称、头像及缺失平台链接发现与规范化 |
| `clean-authors.py` | 根据已部署作者边界清理和整理作者，涉及引用及 ID |
| `find-duplicate-authors.py`、`find-duplicate-videos.py` | 查重检查；结果不能直接视为可删除数据 |
| `check-repost-urls.py`、`fix-urls.py`、`av-to-bv.py` | 链接检查或修复，各自读写行为不同 |
| `import-author-comments.py`、`export-author-comments.py`、`import-date.py`、`export-database.py` | 备注、日期及数据导入导出 |
| `updatelog.py`、`content.log` | 根据统计生成公告并记录历史统计 |
| `upload.sh`、`dolt-push.sh` | 发布工具；不是测试入口 |
| `dump-cookies.sh` | 获取本地认证材料，不记录其输出内容到文档或测试 |

## 数据写入边界

- 优先通过明确的数据库参数指向临时库；参数名并不一致，例如多数工具用 `--db-path`，`clean-authors.py` 用 `--db`。部分工具没有路径参数，必须先检查实现。
- 默认路径有历史差异，不能仅设置 `PROJECT_ROOT` 就假定所有工具都指向正确数据库。某些 sqlite3.connect 调用还会在路径错误时创建空库。
- `csv-import.py` 支持 `--dry-run`、`--skip-metadata`、`--workers` 及 cookies 参数。dry-run 不等于无网络；原/转载元数据获取与数据写入分别确认。
- CSV 导入存在逐步提交及中断时提交已完成记录的行为。改变并发实现时保持匹配、确认与提交顺序，不能将“并发取元数据”变成无序写库。
- 作者整理保留作者 0、外键关系和已部署作者 ID 的约束；`content.log` 的历史数据还被用于确定边界，不能只当普通运行日志删除。
- 作者链接补全只填缺失平台链接，冲突候选不得擅自选择；修改 `author_links.py` 时检查 URL 规范化、重定向、主页结构解析和备份行为。
- 备份应包含已提交 WAL 内容。新增备份优先使用 SQLite backup，不把主文件复制当作一致快照。既有事务、回滚、备份及 dry-run 行为必须按具体工具验证。

## 公告与发布

- `updatelog.py` 读取数据库统计和 `content.log`，向 `frontend/src/data/announcements.js` 前置条目，再追加统计记录；还会查询本地 Dolt 历史生成链接。
- 保持公告数据结构与 `AnnouncementsView.vue` 一致，文本和链接须正确序列化，不能拼接 Vue 模板 HTML。调整统计时同时核对 `backend/src/queries.cjs`。
- `content.log` 为 Git 明确保留的业务历史文件，不应在测试或格式化中顺带改写。
- `upload.sh` 默认上传代码并远程部署；`database-only` 走独立快照与替换流程。修改它时阅读 [部署指南](../../deploy/AGENTS.md)，同步运行包清单与部署测试；不要执行真实上传验证。

## 验证

从根目录执行 `npm run test:python`。现有脚本测试主要在 `test/update/scripts/test_updatelog.py`；它不是 CSV 导入、作者清理或所有元数据工具的完整回归。

修改其他脚本时，按真实风险在 `test/update/scripts/` 补充临时库、CSV 或模拟网络测试。上传脚本运行 `npm run test:deploy`；纯文档调整只检查引用和 diff。
