# 自动抓取流水线指南

适用于本目录，同时遵守 [上级指南](../AGENTS.md)。本流水线输出待审核表格数据，不直接写网站数据库。

## 阶段和配置

| 阶段                         | 实现与配置                               |
| ---------------------------- | ---------------------------------------- |
| RSS 抓取、标签过滤和去重     | `fetcher.py`、`config/fetcher.jsonc`     |
| 获取简介、提取原链接和作者   | `processor.py`、`config/processor.jsonc` |
| 本地合并、上传及在线表格整理 | `upload.py`、`config/upload.jsonc`       |
| CLI 时间范围解析             | `time_range.py`，三个主程序共用          |

配置是 JSONC/JSON5，保留注释和人工维护的用户规则。不要为了统一格式丢失关键字顺序或覆盖优先级。

- fetcher、processor 从脚本目录定位主要配置；upload 的 `config/`、`output/` 及 `config/.env` 相对当前工作目录。运行 upload 时应以本目录为工作目录，不能假定从仓库根目录启动等价。
- 三个程序均支持 `--time-range`，命令行优先于配置。processor 的空配置回退到指定 fetch 配置；upload 当前加载固定的 `config/fetcher.jsonc`，不能仅凭配置注释推断它支持相同的路径覆盖。
- 时间范围支持 today、yesterday、all、具体日期和最近 N 个自然日；fetcher 和 processor 使用北京时间，upload 存在本地 datetime 用法。维护时逐个检查日期边界，不擅自统一历史行为。

## 抓取可靠性

- fetcher 综合每用户 `seen_bvids` 与已有 CSV 的 BV 去重；重复执行应补抓新投稿并保留人工补充的已有单元格。
- CSV 及状态文件通过临时文件和 `os.replace` 更新；新视频仅在 CSV 写入成功后进入已处理状态。标签请求失败需允许下次重试，不能当作明确不匹配永久跳过。
- 翻译状态支持固定值或按标题关键字依次匹配，用户配置覆盖全局默认；空回退需保留为空。标签过滤与标题匹配是不同阶段。
- 保留 RSS/API 请求 timeout、重试及退避配置。网络失败不应破坏已有 CSV 或阻断其他用户的抓取。
- `yesterday` 仅选择昨天一个自然日；fetcher 按视频发布时间筛选，processor/upload 按 CSV 文件名日期筛选。补抓昨天的视频仍写入今天的 CSV，后续处理该批数据应使用 `--time-range today`。
- 输出文件按抓取当天的北京时间命名，不等于视频发布日期；修改选取规则时检查下游按文件日期处理的行为。

## 信息处理和上传副作用

- processor 按配置顺序提取原链接，命中即停止；链接清理、原作者获取、cookies、skip_existing 及请求间隔均有独立行为。修改规则时验证分 P、原视频身份和人工填写数据不被误覆盖。
- processor 调用 yt-dlp，并可能原地写 CSV。仅运行解析测试不应触发实际视频请求。
- upload 默认执行本地合并 → 上传 → 在线整理。`--check-only`（别名 `--local-only`）仍写本地 combined CSV，但不上传；`--upload-only` 上传既有合并文件并整理；`--order-only` 直接整理在线表格。
- `--dry-run` 不能当成无副作用执行：常规流程仍生成合并 CSV，在线整理可能读取远程表格。测试必须模拟网络并将输出定位到临时目录。
- 保留完全相同行去重、分组、空行及表格单元格转换规则；在线整理涉及批量修改，测试应核对请求内容和顺序，不能拿真实表格试运行。
- `config/.env` 中的腾讯文档认证、cookies、状态和输出仅留本地。不要在报错、夹具或文档中复制令牌及 cookie 内容。

## 验证

从根目录运行 `python -m unittest discover -s test/update/autofetch -v` 或 `npm run test:python`。现有测试覆盖请求超时、重试配置、时间范围 CLI、状态与 CSV 合并等；不代表对处理与在线上传全部行为完成回归。新增验证放入 `test/update/autofetch/`，使用临时路径和模拟 requests/yt-dlp。
