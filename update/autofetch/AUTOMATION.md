# 定时运行

以下示例使用 SSH 别名 `server`、普通用户 `user` 和部署目录 `/home/user/autofetch`，请替换为自己的主机、用户和目录。部署命令显式指定 `--target`，避免使用脚本内的默认路径。

```sh
python deploy-autofetch.py --host server --target /home/user/autofetch
```

脚本通过 SSH 上传明确列出的源码与配置，在目标服务器上准备独立 Python 环境、检查配置、安装当前用户的 cron。NixOS 默认使用 Nix，`.runtime` 链接固定运行环境以避免被 GC；其他系统默认使用 venv。首次构建需要能访问 Nix 缓存或 Python 包源。它不会执行抓取、上传或邮件测试。

第一次若缺少认证配置，脚本会生成统一的 `.env` 配置模板并停止，不安装新 cron。填写服务器的 `config/.env` 和 cookies 后重新运行同一命令即可。也可以先在本地填好文件，然后显式传输凭据：

```sh
python deploy-autofetch.py --host server --target /home/user/autofetch --with-secrets
```

使用 `--with-secrets` 更新 `.env` 时，本地代理字段缺失、注释或值为空（含空引号），均保留服务器的对应代理；本地非空值才覆盖。适用于大小写形式的 `http_proxy`、`https_proxy`、`all_proxy` 和 `no_proxy`。需要清除代理时直接编辑服务器 `.env`。其他认证字段仍按本地文件更新。

默认不传凭据，不覆盖服务器已有 JSONC，不同步或删除 state/output。需要更新配置规则时显式加 `--replace-config`。支持 `--target /绝对路径` 和 `--backend nix|venv`。如果已在目标服务器上，省略 `--host` 就是本地部署；请以拥有部署目录写入权限的普通用户运行，不用 sudo。

部署会保留无关 cron 条目，并用 `# autofetch-managed` 标记替换自身条目。部署前的 crontab 保存在 `state/automation/crontab.before-deploy.txt`。若任务正在运行则拒绝部署，等待任务结束后重试。配置校验失败不替换 cron；已有源码和运行环境可能已更新，修正后须重新部署完成检查。

## 手动安装（可选）

将整个 autofetch 目录放在 `/home/user/autofetch`，在目标服务器上创建 Python 环境：

```sh
cd /home/user/autofetch
python3 -m venv .venv
.venv/bin/pip install requests json5 yt-dlp
test -f config/.env || cp config/.env.example config/.env
chmod 600 config/.env cookies.txt
```

在 `config/.env` 中填写腾讯文档认证以及 163 SMTP 发件账户、授权码和收件地址。已有 `.env` 只需按 `config/.env.example` 补上邮件字段，不要覆盖原有认证；B 站 cookies 仍按 processor 配置读取。不要提交这些文件。cron 环境需要可用的 `python3` 创建 venv；若 NixOS 未提供，先在含 Python 的开发环境完成安装，确保 `.venv/bin/python` 在退出环境后仍可执行。

先安装代码并运行自动测试，再用 `crontab -e` 添加以下一整行（需先安装并启用 cron 服务）：

```cron
* * * * * /usr/bin/env PATH=/home/user/autofetch/.venv/bin:/run/current-system/sw/bin:/usr/bin:/bin TZ=Asia/Shanghai /home/user/autofetch/.venv/bin/python /home/user/autofetch/automation.py >> /home/user/autofetch/automation.log 2>&1
```

入口内部使用北京时间，与 cron 的本地时区无关。每分钟检查到期任务；进程锁阻止并发运行。该命令会真实抓取并上传，不要用它测试配置。

## 代理

手动脚本和自动任务均读取 `config/.env`，无需先 `source`。例如：

```dotenv
http_proxy=http://127.0.0.1:7890
https_proxy=http://127.0.0.1:7890
no_proxy=localhost,127.0.0.1
```

将端口替换为运行服务器上的 HTTP 代理端口。processor 启动的 yt-dlp 会继承代理，fetcher 和 upload 的 requests 请求也会使用代理。已有同名环境变量优先于 `.env`；建议统一使用小写变量名。`no_proxy` 可填逗号分隔的直连主机，例如 RSSHub 或 `docs.qq.com`。SMTP 邮件发送不使用 HTTP 代理。

修改后在下一次进程启动时生效，已运行的任务不受影响。默认部署保留服务器 `.env`；在服务器修改，或使用 `--with-secrets` 显式同步本地版本。代理地址若含账号密码，不要提交或贴到日志中。

## 调度和状态

- 周一至周六 23:00 抓今天和昨天；周日 23:00 只抓周日。
- 周日 00:10 单独补抓周六；03:00 停止并生成收尾状态。到时仍未解决则失败并发邮件，等待人工处理。
- 日常任务最多 6 轮（含首次），失败后等待 10 分钟。凌晨收尾每轮后等待 10 分钟，直到成功或截止。每轮最长 15 分钟，超时终止整个子进程组。
- 目标日期在创建任务时固定，跨午夜重试不会变成另一天。中断会消耗一次尝试；未完成的日常任务保留供后续检查继续。周日 03:00 前会补建遗漏的周六 23:00 任务，周六日常任务同样在周日 03:00 截止；其他整日停机不自动补建历史任务，应人工核对。
- 数据按周日至周六隔离在 `state/automation/weeks/`；定时输出按目标投稿日期命名，原脚本默认输出日期行为不变。凌晨补回的周六内容仍归上周，不混入周日新批次。
- `state/automation/jobs.json` 是任务状态，`closeout.json` 是周末收尾结果。每个任务目录有日志及抓取/补全 JSON 报告。完整完成只表示 RSS 返回内容无未解决错误，不能保证 RSS 没有截断、缓存或漏项。
- 周末仍失败时只记录与提醒，不自动继续补旧批次。邮件失败记录在任务的 `mail` 字段和 cron 日志，同一失败任务不反复发信。

以下状态查询和续跑示例使用 venv；自动部署若使用 Nix 后端，将 `.venv/bin/python` 替换为 `.runtime/bin/python`。

只读查看状态：

```sh
cd /home/user/autofetch
.venv/bin/python automation.py --status
```

人工续跑（会真实上传，并解除凌晨截止；任务日期、周归属和上传检查点不变）：

```sh
.venv/bin/python automation.py --retry 20261108-closeout
```

## 上传与故障恢复

仅上传本周尚未确认上传的完整行，上传前和在线整理均按作者名自然排序，同一作者内按视频标题自然排序：忽略字母大小写，阿拉伯数字和中文数字均按数值比较（如第2话在第10话前、第二话在第十话前），支持十百千万亿单位；其他字符按 Unicode 顺序，不转换为拼音；排序键相同则保留输入顺序。保留分组、去重和空行规则。抓取有部分失败时，已抓取且补全完成的数据仍可上传，剩余部分下一轮继续；补全未完成时该周暂不上传。没有新增数据是正常完成，不上传空表。

上传前严格读取远端并确定追加位置，再保存待上传批次；读取失败绝不能视为空表。上传请求失败或进程中断后，下一轮先核对远端新增的完整行数量。确认全部存在才记为成功，否则停止追加并报告 `upload_uncertain`，需要人工检查。它不会因为“看起来没写入”而盲目重传。

检查不确定批次时，先禁用 cron 并备份整个 `state/automation`。对照该周 `uploaded.json` 中的 `pending`、`pending_payload`、`baseline` 与远端数据：确认原请求全部写入后可续跑自动核对；确认完全未写入后才可人工把 `pending` 置为 `null` 再续跑。部分写入必须先人工核对并修正，不能直接清除检查点。在线整理失败独立重试，不重新追加已确认内容。

这是新的一套独立运行状态。启用前不要在同一周混用手动上传与自动上传；已有在线数据须先人工核对，避免迁移首次运行时重复收录。不要删除状态文件、把自动任务当成抓齐整周的证明，或以真实表格试运行代码。

邮件使用 Python 自带 `smtplib`，通过 `smtp.163.com:465` 的 TLS 连接发送。上传阶段首次失败立即发送；抓取和补全仍在最终失败时发送。每个任务最多通知一次，上传失败后仍保留原有重试和检查点核对。正文限阶段代码、失败 UID/BV、目标日期和本地路径，不附原始日志或凭据。未执行真实测试发信；需确认收件地址后单独授权。
