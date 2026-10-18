# 测试维护指南

适用于 `test/`，同时遵守 [根目录指南](../AGENTS.md)。详细操作见 [README.md](README.md)；可执行命令以本目录 `package.json` 为准。

## 组织与工具

| 路径 | 职责 |
| --- | --- |
| `frontend/unit/` | Vitest：纯逻辑、Vue 生命周期、请求封装和基础设施 |
| `frontend/e2e/` | Playwright：交互行为与多宽度截图 |
| `frontend/fixtures/` | 固定 API 数据、浏览器请求模拟与旧前端逻辑参照 |
| `backend/` | Node test runner：缓存、搜索、API 对照及合成数据 benchmark |
| `backend/fixtures/` | SQLite 数据构造与冻结旧后端的沙箱 |
| `update/` | unittest：公告生成及 autofetch 行为 |
| `deploy/` | unittest：代码部署、数据库上传替换及 Nginx 集成 |
| `results/`、`reports/`、`.cache/` | 本地产物，受 Git 忽略 |

新增测试、夹具、测试专用依赖和配置都放在本目录。生产目录和根目录保留转发命令即可；不要另设不被现有命令发现的测试目录。

## 环境及运行

根目录分别安装 frontend、backend、test 的依赖；Python 依赖和浏览器需单独准备。根目录命令与本目录脚本对应关系为：

| 根目录命令 | 实际覆盖 |
| --- | --- |
| `npm --prefix test test` | 前端 Vitest 单元测试 |
| `npm run test:backend` | `node --test backend/*.test.cjs` |
| `npm run test:python` | `update/` 下 Python unittest |
| `npm run test:deploy` | `deploy/` 下 Python unittest |
| `npm test` | 上述四类依次执行，不包含浏览器和 benchmark |
| `npm run test:e2e` | behavior.spec.js |
| `npm run test:visual` | visual.spec.js，与已有本地基线比较 |
| `npm run bench:backend` | 合成内存数据性能对照与结果一致性检查 |

- Python 测试使用 requests、json5，公告测试还调用 Node。部署测试需要 rsync；Nginx 测试没有二进制时会跳过，可通过 `NGINX_BIN` 指定。
- Playwright 自动启动 `127.0.0.1:4173` 的 Vite 服务；使用 Chromium，可通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 指定程序。配置固定 locale 为 zh-CN、时区为 Asia/Shanghai。
- Vitest 的 Vue 别名指向 frontend 依赖，保证 composables 与生命周期测试使用同一 Vue 实例；移动依赖或配置时不能引入两份实例。

## 夹具与隔离

- 测试仅使用固定数据、内存或临时数据库。后端 API 测试在临时端口监听，结束后清理服务、计时器和连接。
- 前端浏览器请求由 `frontend/fixtures/api.js` 模拟，不能在回归中访问真实后端、B 站或在线表格。需要的新响应和失败场景在夹具中显式建模。
- Python 维护工具测试使用临时目录及模拟网络/子进程；导入某些脚本会读取环境或配置，测试需控制 cwd、环境和模块搜索路径并在结束时恢复。
- 部署回归只在临时目录执行。保留真实 rsync 对复制行为的验证，模拟服务及远程命令，不把真实数据库、服务器或凭据带进夹具。
- `frontend/fixtures/legacy-logic.js` 与 `backend/fixtures/legacy-server.cjs` 为冻结参照；重构不能同步修改它们来消除差异。旧后端只通过 `legacy.cjs` 沙箱运行，不直接启动。
- benchmark 使用合成内存数据并验证结果、索引复用等行为，时间测量仅作本机参考。不要增加依赖真实网络或线上数据库的性能基准。

## 截图和预期变更

- 截图覆盖 390、768、834、1440 像素，要求相同浏览器、系统与字体；只隐藏动态 Sakana 挂件，不额外隐藏待验证界面。
- `*-snapshots/` 基线及实际图片都仅存本地。缺少基线时如实报告；应在认可的代码版本先生成基线，再改动并比较。
- `npm run test:visual:update` 用于明确认可的基线更新，不用于消除未解释的差异。更改产品预期前先确认业务行为，旧参照不随之重写。
- 测试应验证有意义的行为和失败边界，避免机械复述实现。验证完成报告实际运行范围、跳过和环境限制，不将某个子集通过说成全套通过。
