#!/usr/bin/env python3
"""Install autofetch locally or over SSH. Never run the pipeline during deployment."""

import argparse
import fcntl
import io
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
FILES = [
    "fetcher.py",
    "processor.py",
    "upload.py",
    "time_range.py",
    "env.py",
    "automation.py",
    "deploy-autofetch.py",
    "AUTOMATION.md",
    "config/.env.example",
]
CONFIGS = [f"config/{name}.jsonc" for name in ("fetcher", "processor", "upload")]
SECRETS = ["config/.env", "cookies.txt"]
MARKER = "# autofetch-managed"
NIX_ENV = """let
  pkgs = (builtins.getFlake "nixpkgs").legacyPackages.${builtins.currentSystem};
in pkgs.python3.withPackages (ps: [ ps.requests ps.json5 ps.yt-dlp ])"""


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def copy_file(source, target):
    if source.resolve() == target.resolve():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".deploy.tmp")
    shutil.copyfile(source, temporary)
    temporary.chmod(0o600)
    temporary.replace(target)


def cron_text(old, target, python):
    # Percent is special even inside shell quotes in a crontab command.
    if any(c in str(target) + str(python) for c in "\n\r%"):
        raise ValueError("部署路径不能含换行或 %")
    command = shlex.join([str(python), str(target / "automation.py")])
    search_path = shlex.quote(
        str(python.parent) + ":/run/current-system/sw/bin:/usr/bin:/bin"
    )
    line = f"* * * * * PATH={search_path} {command} >> {shlex.quote(str(target / 'automation.log'))} 2>&1 {MARKER}"
    existing = [line for line in old.splitlines() if not line.rstrip().endswith(MARKER)]
    return "\n".join(existing + [line]) + "\n"


def validate(target, python):
    # Validate in the installed interpreter; no RSS, video or mail requests.
    code = """
import json5, requests, yt_dlp, os
from pathlib import Path
import upload
required = ["TENCENT_DOCS_ACCESS_TOKEN", "TENCENT_DOCS_CLIENT_ID", "TENCENT_DOCS_OPEN_ID",
            "AUTOFETCH_MAIL_FROM", "AUTOFETCH_MAIL_TO", "AUTOFETCH_MAIL_USER", "AUTOFETCH_MAIL_PASSWORD"]
missing = [key for key in required if not os.environ.get(key) or
           os.environ[key].startswith(("replace-", "your-account", "recipient@example"))]
if missing:
    raise SystemExit("缺少本地认证设置：" + ", ".join(missing))
for name in ("fetcher", "processor", "upload"):
    config = json5.loads(Path(f"config/{name}.jsonc").read_text())
    if name == "fetcher" and not config.get("users"):
        raise SystemExit("fetcher users 为空")
    if name == "upload" and not all(config.get(k) for k in ("file_id", "sheet_id")):
        raise SystemExit("缺少腾讯文档 file_id/sheet_id")
    if name == "processor" and config.get("cookies", {}).get("enabled"):
        cookie = Path(config["cookies"].get("file", "cookies.txt"))
        if not cookie.is_file():
            raise SystemExit("缺少 processor 配置指定的 cookies 文件")
"""
    run([str(python), "-c", code], cwd=target)


def install(target, backend, replace_config=False, with_secrets=False):
    target = target.expanduser().absolute()
    target.mkdir(parents=True, exist_ok=True)
    state = target / "state" / "automation"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("任务正在运行，请结束后重试部署") from None
        # Read crontab before touching installed files; do not treat permission errors as empty.
        current = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            env={**os.environ, "LC_ALL": "C"},
        )
        if current.returncode and not (
            current.returncode == 1 and "no crontab for" in current.stderr.lower()
        ):
            raise RuntimeError("无法读取 crontab；请确认 cron 可用且当前用户有权限")
        if backend == "auto":
            backend = "nix" if Path("/etc/NIXOS").exists() else "venv"
        if backend == "nix":
            # The out-link is also a persistent GC root, independent of oix.
            run(
                [
                    "nix",
                    "build",
                    "--impure",
                    "--expr",
                    NIX_ENV,
                    "--out-link",
                    str(target / ".runtime"),
                ]
            )
            python = target / ".runtime" / "bin" / "python"
        else:
            run([sys.executable, "-m", "venv", str(target / ".venv")])
            python = target / ".venv" / "bin" / "python"
            run([str(python), "-m", "pip", "install", "requests", "json5", "yt-dlp"])
        for name in FILES:
            copy_file(SOURCE / name, target / name)
        for name in CONFIGS:
            if replace_config or not (target / name).exists():
                copy_file(SOURCE / name, target / name)
        if with_secrets:
            for name in SECRETS:
                if (SOURCE / name).is_file():
                    copy_file(SOURCE / name, target / name)
        dotenv = target / "config" / ".env"
        if not dotenv.exists():
            copy_file(SOURCE / "config/.env.example", dotenv)
        for name in SECRETS:
            if (target / name).is_file():
                (target / name).chmod(0o600)
        # This check may stop an initial install; an existing crontab is never replaced on failure.
        validate(target, python)
        run(
            [
                str(python),
                "-m",
                "py_compile",
                *[str(target / name) for name in FILES if name.endswith(".py")],
            ]
        )
        content = cron_text(
            current.stdout if current.returncode == 0 else "", target, python
        )
        backup = state / "crontab.before-deploy.txt"
        backup.write_text(current.stdout if current.returncode == 0 else "")
        backup.chmod(0o600)
        run(["crontab", "-"], input=content, text=True)
    print(f"已部署到 {target}，已安装每分钟检查任务的 cron；未执行抓取、上传或发信。")


def remote(host, target, backend, replace_config=False, with_secrets=False):
    if host.startswith("-") or any(c in host for c in "\n\r"):
        raise ValueError("无效 SSH 主机名")
    names = FILES + CONFIGS
    if with_secrets:
        names += [name for name in SECRETS if (SOURCE / name).is_file()]
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as archive:
        for name in names:
            archive.add(SOURCE / name, arcname=name, recursive=False)
    options = ["--target", str(target), "--backend", backend]
    if replace_config:
        options.append("--replace-config")
    if with_secrets:
        options.append("--with-secrets")
    # stdin carries only our allowlisted archive. All dynamic shell arguments are quoted.
    script = """set -eu
umask 077
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
tar -xzf - -C "$stage"
if command -v python3 >/dev/null 2>&1; then
  python3 "$stage/deploy-autofetch.py" OPTIONS
elif command -v nix >/dev/null 2>&1; then
  nix shell nixpkgs#python3 --command python3 "$stage/deploy-autofetch.py" OPTIONS
else
  echo '服务器需要 Python 3 或 Nix' >&2
  exit 1
fi
""".replace("OPTIONS", shlex.join(options))
    run(["ssh", host, "bash -c " + shlex.quote(script)], input=payload.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="SSH 别名，例如 voile；省略则在当前机器部署")
    parser.add_argument("--target", default="/home/howl/autofetch")
    parser.add_argument("--backend", choices=["auto", "nix", "venv"], default="auto")
    parser.add_argument(
        "--replace-config",
        action="store_true",
        help="用源码内 JSONC 覆盖目标配置；默认保留",
    )
    parser.add_argument(
        "--with-secrets",
        action="store_true",
        help="同时复制现有 .env、邮件认证与 cookies；默认不传凭据",
    )
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.host:
            remote(
                args.host,
                Path(args.target),
                args.backend,
                args.replace_config,
                args.with_secrets,
            )
        else:
            install(
                Path(args.target), args.backend, args.replace_config, args.with_secrets
            )
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        # Do not echo CalledProcessError.cmd: it may contain secrets in future extensions.
        print(
            f"部署未完成：{error if isinstance(error, (RuntimeError, ValueError)) else type(error).__name__}",
            file=sys.stderr,
        )
        print("未执行抓取、上传或发信；请修正配置后重新部署。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
