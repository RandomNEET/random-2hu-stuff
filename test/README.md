# 测试

所有测试代码、夹具、配置和本地产物集中在此目录。

```text
test/
  frontend/
    unit/       # 业务逻辑与 Vue 生命周期测试
    e2e/        # 浏览器交互与截图测试，含本地截图基线
    fixtures/   # 固定 API 数据和重构前逻辑参照
  backend/      # 缓存、搜索、接口对照测试与合成数据性能测量
  update/
    scripts/    # 公告生成脚本测试
    autofetch/  # RSS 抓取、日期范围及 CSV 合并测试
  playwright.config.js
  vitest.config.js
  package.json
  results/      # 本地测试输出（Git 忽略）
  .cache/       # 工具缓存（Git 忽略）
```

## 安装与运行

在仓库根目录安装前端和测试工具依赖：

```sh
npm --prefix frontend ci
npm --prefix backend ci
npm --prefix test ci
npm test
```

根目录的 `npm test` 运行前端单元测试、后端测试和 Python 测试。后端接口测试需要本地临时端口，数据仅来自内存或临时 SQLite 数据库，不打开项目数据库。Python 测试沿用更新工具的运行环境，需要 `requests` 和 `json5`；公告测试另用 Node 验证生成的数据模块。

仅运行某一类测试：

```sh
npm --prefix test test
npm run test:python
npm run test:backend
npm run bench:backend
npm run test:e2e
npm run test:visual
```

Python 测试也可直接运行：`python -m unittest discover -s test/update -v`。

`npm run bench:backend` 使用合成的内存数据库比较重构前后的查询时间和索引构建次数，并验证结果一致；不会测量线上数据库或发出外部网络请求。

浏览器测试首次使用前，在 `test/` 中运行 `npx playwright install chromium`。已有 Chromium 时，通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 指定浏览器程序。Playwright 会自动在 `frontend/` 启动本地开发服务，不修改真实数据库或执行上传。

## 截图基线

截图比较覆盖 390、768、834、1440 像素宽度，要求相同浏览器、系统和字体。截图时仅隐藏动态 Sakana 挂件。

`frontend/e2e/*-snapshots/` 的基线、`results/` 的实际图片和差异图片均被 Git 忽略。基线仅留本地，新检出项目需先在认可的代码版本运行 `npm run test:visual:update`，再修改代码并运行 `npm run test:visual`。缺少基线时比较会失败，不会自动接受新图片；不要用更新基线掩盖未解释的差异。

`frontend/fixtures/legacy-logic.js` 是重构前行为的冻结参照，不应随实现修改。

前端目录原有的 `npm test`、`npm run test:e2e` 和截图命令继续可用，它们转发到本目录。

部署脚本回归：`npm run test:deploy`（仓库根目录）。使用临时目录、真实 rsync 和模拟服务命令，验证代码复制、数据库及 WAL/SHM 保留和构建失败时不更新线上文件；不连接服务器。需要本地 rsync。

Nginx 集成测试见 `deploy/nginx.md`，通过 `NGINX_BIN` 指定二进制；缺少 Nginx 时跳过。测试只启动本地临时服务。

数据库独立上传回归：`python -m unittest discover -s test/deploy -p test_database_upload.py -v`。使用临时 SQLite 文件与模拟 PM2/健康检查，覆盖替换、备份、无效文件拒绝及失败恢复；不连接生产环境。
