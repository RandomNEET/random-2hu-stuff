# 部署维护指南

适用于 `deploy/`，同时遵守 [根目录指南](../AGENTS.md)。本目录操作真实服务、文件及数据库；修改脚本使用临时环境回归，未授权发布时不执行线上命令。

## 各入口的边界

| 文件                             | 职责                                                                    |
| -------------------------------- | ----------------------------------------------------------------------- |
| `deploy.sh`                      | 将源码构建并部署到既有 Debian 环境，支持 all、frontend、backend、status |
| `replace-database.sh`            | 接收单独上传的一致快照，校验、备份、切换并在失败时恢复                  |
| `get-db.sh`                      | 从 DoltHub 导出 SQLite，删除并重建目标输出文件                          |
| `nginx.conf`                     | HTTPS、SPA 路由、API 代理与静态缓存配置样例                             |
| `../backend/ecosystem.config.js` | PM2 进程与日志配置                                                      |
| `../update/scripts/upload.sh`    | 本地打包、源码上传、远程调用部署或单独上传数据库                        |

## 代码部署不变量

- `deploy.sh` 要求 root、Debian、既有 Nginx 配置和相关工具；后端部署还要求已有数据库及 PM2 进程。它不是全新服务器的一键初始化脚本。
- 默认源码根目录来自脚本位置或 `PROJECT_ROOT`，线上目标为 `/var/www/random-2hu-stuff`，支持 `DEPLOY_TARGET`；来源和目标必须不同。默认进程为 `r2s-api`，健康检查为本地 3000 端口 `/health`。
- 前端构建及后端原生依赖安装、加载检查完成后才能更改线上代码；失败不能留下半部署的文件。
- 代码备份不包含数据库、node_modules 或环境凭据；后端复制不在根目录使用删除同步，不删除或修改数据库及 WAL/SHM 的所有权。
- 前端保留旧哈希资源，使已打开页面继续加载；不要无意加上 `--delete`。Nginx 配置保持人工管理，部署脚本不能直接覆盖。
- 新增后端运行文件时同步 `deploy.sh` 与 `upload.sh` 的复制清单；验证打包包含 `server.cjs`、`src/`、package 清单和 PM2 配置。
- 上传源码使用独立远程目录，不能把源码同步目标改为线上应用目录。保留现有 SSH agent 复用及只清理自身 agent 的逻辑。

## 数据库替换不变量

- 上传端使用 SQLite backup 获取包含已提交 WAL 的快照，不单独复制主文件或上传本地 sidecar。
- 替换端先检查候选路径、完整性和所需列，再停止服务；无效文件应在停服前拒绝。
- 旧数据库备份通过 SQLite backup 生成，并保留所有权和权限。只有停服后才能清理旧 sidecar 并切换文件。
- 切换前设置恢复标记；切换或健康检查失败应恢复旧库并尝试重启。调整 trap 和状态变量时逐条检查失败分支，不能仅验证成功路径。
- `get-db.sh` 会删除已有输出，不是热替换流程，不可用于验证线上更新；测试使用显式临时输出路径。

## Nginx 行为

- `/api/` 和 `/health` 代理到本地后端，不加额外代理缓存。健康检查使用 no-store。
- history 路由允许回退到 index.html，但缺失静态资源必须返回 404。保留隐藏文件及编辑器备份文件的拒绝规则。
- 仅成功的内容哈希资源使用长期 immutable 缓存；其他内容重新验证，5xx 禁止缓存。
- 安全头保持在同一层级，避免 location 内 add_header 导致 Debian Nginx 的继承规则丢失父级头；修改代理 keepalive 时检查 Node 空闲超时。

## 验证

根目录运行 `npm run test:deploy`。测试使用临时目录、真实 rsync、模拟 PM2/健康检查；不会连接服务器。Nginx 集成测试需要本地二进制，可用 `NGINX_BIN` 指定，缺少时会跳过。

脚本修改可另执行 `bash -n deploy/deploy.sh deploy/get-db.sh deploy/replace-database.sh update/scripts/upload.sh`。语法检查不能替代部署回归。Nginx 回归细节见 `test/deploy/test_nginx.py`。
