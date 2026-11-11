#!/usr/bin/env python3
"""Cron entry point. All scheduling uses Beijing time; no daemon is required."""

import argparse
import copy
import fcntl
import json
import os
import signal
import smtplib
import ssl
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from env import load_dotenv

ROOT = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
DATA = ROOT / "state" / "automation"
LOCK_FD = None


def now():
    return datetime.now(TZ)


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, value):
    from fetcher import save_state

    save_state(path, value)


def week(date):
    return (date - timedelta(days=(date.weekday() + 1) % 7)).strftime("%Y%m%d")


def dates_for(date):
    return [date] if date.weekday() == 6 else [date - timedelta(days=1), date]


def discover(state, current):
    """Create due jobs only; previous jobs retain their fixed dates across midnight."""
    date = current.date()
    candidates = [(date, "daily")]
    if date.weekday() == 6:
        candidates.append((date, "closeout"))
        if current.hour < 3:
            candidates.append((date - timedelta(days=1), "daily"))
    for date, kind in candidates:
        start = datetime.combine(date, datetime.min.time(), TZ)
        start += timedelta(minutes=10) if kind == "closeout" else timedelta(hours=23)
        key = f"{date:%Y%m%d}-{kind}"
        if current < start or key in state:
            continue
        targets = [date - timedelta(days=1)] if kind == "closeout" else dates_for(date)
        deadline = (
            datetime.combine(date, datetime.min.time(), TZ) + timedelta(hours=3)
            if kind == "closeout"
            else None
        )
        if kind == "daily" and date.weekday() == 5:
            deadline = datetime.combine(
                date + timedelta(days=1), datetime.min.time(), TZ
            ) + timedelta(hours=3)
        state[key] = {
            "dates": [d.strftime("%Y%m%d") for d in targets],
            "kind": kind,
            "attempts": 0,
            "status": "pending",
            "next": start.isoformat(),
            "deadline": deadline.isoformat() if deadline else None,
        }


def execute(command, log, deadline=None):
    seconds = min(7200, (deadline - now()).total_seconds()) if deadline else 7200
    if seconds <= 0:
        raise RuntimeError("deadline")
    # Kill the entire process group, including yt-dlp, before releasing the lock.
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log,
        stderr=log,
        start_new_session=True,
        pass_fds=(() if LOCK_FD is None else (LOCK_FD,)),
    )
    try:
        code = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise RuntimeError("deadline_or_stage_timeout") from None
    if code:
        raise RuntimeError(f"{Path(command[1]).name}: exit {code}")


def read_remote(config):
    """Fail closed: a failed/partial remote read must never mean an empty sheet."""
    import requests
    import upload

    if not all([upload.ACCESS_TOKEN, upload.CLIENT_ID, upload.OPEN_ID]):
        raise RuntimeError("missing_upload_credentials")
    headers = {
        "Access-Token": upload.ACCESS_TOKEN,
        "Client-Id": upload.CLIENT_ID,
        "Open-Id": upload.OPEN_ID,
    }
    base = f"https://docs.qq.com/openapi/spreadsheet/v3/files/{config['file_id']}"
    response = requests.get(base, headers=headers, timeout=20)
    response.raise_for_status()
    body = response.json()
    if body.get("code", 0) != 0:
        raise RuntimeError("invalid_sheet_metadata")
    props = [
        p
        for p in body.get("properties", [])
        if str(p.get("sheetId")) == str(config["sheet_id"])
    ]
    if len(props) != 1:
        raise RuntimeError("invalid_sheet_metadata")
    count = int(props[0]["rowCount"])
    rows = []
    for start in range(0, count, 500):
        end = min(start + 500, count)
        response = requests.get(
            f"{base}/{config['sheet_id']}/A{start+1}:Z{end}",
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("code", 0) != 0 or "rows" not in body.get("gridData", {}):
            raise RuntimeError("invalid_sheet_rows")
        chunk = body["gridData"]["rows"]
        # Missing rows may be trailing blanks, but cannot safely establish placement.
        if len(chunk) != end - start:
            raise RuntimeError("incomplete_sheet_read")
        rows.extend(
            [[cell.get("cellValue") for cell in row.get("values", [])] for row in chunk]
        )
    return rows


def cell_text(cell):
    if not cell:
        return ""
    if "link" in cell:
        return str(cell["link"].get("url", "")).strip()
    return str(cell.get("text", cell.get("number", ""))).strip()


def signature(row):
    values = [str(v).strip() for v in row]
    while len(values) > 5 and not values[-1]:
        values.pop()
    return tuple(values + [""] * max(0, 5 - len(values)))


def upload_week(directory):
    import upload

    config = upload.load_upload_config()
    ledger_path = directory / "uploaded.json"
    ledger = load(
        ledger_path, {"confirmed": [], "pending": None, "order_pending": False}
    )
    remote = None
    if ledger["pending"]:
        remote = read_remote(config)
        present = Counter(signature([cell_text(c) for c in row]) for row in remote)
        pending = Counter(signature(row) for row in ledger["pending_payload"] if row)
        before = Counter({tuple(k): v for k, v in ledger["baseline"]})
        if pending - (present - before):
            raise RuntimeError(
                "upload_uncertain: 核对远端后人工处理 pending，禁止盲目重传"
            )
        ledger["confirmed"].extend(ledger["pending"])
        ledger["pending"] = None
        ledger["order_pending"] = True
        save(ledger_path, ledger)
    if ledger["order_pending"]:
        if not upload.order_sheet(config["file_id"], config["sheet_id"], dry_run=False):
            raise RuntimeError("online_order_failed")
        ledger["order_pending"] = False
        save(ledger_path, ledger)
    rows = []
    for path in sorted((directory / "output").glob("*.csv")):
        rows.extend(upload.read_csv(path))
    # Use all five columns, preserving split/merged works and human-maintained cells.
    confirmed = {signature(r) for r in ledger["confirmed"]}
    pending = [
        r
        for r in upload.deduplicate(upload.trim_empty_first_column(rows))
        if signature(r) not in confirmed
    ]
    if not pending:
        return
    if remote is None or ledger["confirmed"]:
        remote = read_remote(config)
    last = next(
        (
            i
            for i in range(len(remote) - 1, -1, -1)
            if any(cell_text(c) for c in remote[i])
        ),
        -1,
    )
    payload = upload.process_rows(copy.deepcopy(pending))
    ledger["pending"] = pending
    ledger["pending_payload"] = payload
    ledger["baseline"] = [
        [list(k), v]
        for k, v in Counter(
            signature([cell_text(c) for c in row]) for row in remote
        ).items()
    ]
    save(
        ledger_path, ledger
    )  # Persist before POST: interruption is treated as uncertain.
    if not upload.upload_to_tdocs(
        payload, config, start_row=last + 2 if last >= 0 else 0
    ):
        raise RuntimeError("upload_uncertain")
    ledger["confirmed"].extend(pending)
    ledger["pending"] = None
    ledger["order_pending"] = True
    save(ledger_path, ledger)
    if not upload.order_sheet(config["file_id"], config["sheet_id"], dry_run=False):
        raise RuntimeError("online_order_failed")
    ledger["order_pending"] = False
    save(ledger_path, ledger)


def attempt(key, job):
    directory = DATA / "jobs" / key
    directory.mkdir(parents=True, exist_ok=True)
    deadline = now() + timedelta(minutes=15)
    if job["deadline"]:
        deadline = min(deadline, datetime.fromisoformat(job["deadline"]))
    with (directory / "run.log").open("a") as log:
        weeks = set()
        errors = []
        for date in job["dates"]:
            target = datetime.strptime(date, "%Y%m%d").date()
            batch = DATA / "weeks" / week(target)
            output = batch / "output"
            output.mkdir(parents=True, exist_ok=True)
            weeks.add(batch)
            command = [
                sys.executable,
                str(ROOT / "fetcher.py"),
                "--time-range",
                date,
                "--output-dir",
                str(output),
                "--output-date",
                date,
                "--state-file",
                str(DATA / "fetcher.json"),
                "--report",
                str(directory / f"fetch-{date}.json"),
            ]
            try:
                execute(command, log, deadline)
            except RuntimeError as error:
                errors.append(str(error))
        for batch in sorted(weeks):
            try:
                execute(
                    [
                        sys.executable,
                        str(ROOT / "processor.py"),
                        "--time-range",
                        "all",
                        "--csv-dir",
                        str(batch / "output"),
                        "--report",
                        str(directory / f"process-{batch.name}.json"),
                    ],
                    log,
                    deadline,
                )
            except RuntimeError as error:
                errors.append(str(error))
                continue
            try:
                execute(
                    [
                        sys.executable,
                        str(ROOT / "automation.py"),
                        "--upload-week",
                        batch.name,
                    ],
                    log,
                    deadline,
                )
            except RuntimeError as error:
                errors.append(str(error))
                job["error"] = "upload: " + str(error)
                alert(key, job)
        if errors:
            raise RuntimeError("; ".join(errors))


def notify(key, job):
    import upload

    upload.load_dotenv(ROOT / "config" / ".env")
    message = EmailMessage()
    message["Subject"] = f"[autofetch] {key} 未完成"
    message["From"] = os.environ["AUTOFETCH_MAIL_FROM"]
    message["To"] = os.environ["AUTOFETCH_MAIL_TO"]
    report_dir = DATA / "jobs" / key
    # Never include raw logs, exception bodies, cookies or environment variables.
    details = []
    for path in sorted(report_dir.glob("*.json")):
        report = load(path, {})
        details.append(
            {
                "report": path.name,
                "complete": report.get("complete"),
                "failures": report.get("failures", []),
            }
        )
    message.set_content(
        f"目标日期：{', '.join(job['dates'])}\n重试轮数：{job['attempts']}\n"
        f"状态：{job['status']}\n阶段结果：{job.get('error', 'interrupted')}\n"
        f"日志目录：{report_dir}\n"
        f"手动续跑：cd {ROOT} && {sys.executable} automation.py --retry {key}\n"
        + json.dumps(details, ensure_ascii=False, indent=2)
        + "\n本报告只验证 RSS 返回内容，不能证明平台投稿完整覆盖。\n"
    )
    with smtplib.SMTP_SSL(
        "smtp.163.com", 465, timeout=30, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(
            os.environ["AUTOFETCH_MAIL_USER"], os.environ["AUTOFETCH_MAIL_PASSWORD"]
        )
        smtp.send_message(message)


def alert(key, job):
    """Send at most one failure mail per job, persisting before sending."""
    if job.get("notified"):
        return
    job["notified"] = True
    state_path = DATA / "jobs.json"
    state = load(state_path, {})
    state[key] = job
    save(state_path, state)
    try:
        notify(key, job)
        job["mail"] = "sent"
    except Exception as error:
        job["mail"] = f"failed: {type(error).__name__}"
        print(
            f"{key}: 邮件发送失败（{type(error).__name__}），请查看本地状态",
            file=sys.stderr,
        )
    save(state_path, state)


def tick(retry=None):
    state_path = DATA / "jobs.json"
    state = load(state_path, {})
    current = now()
    discover(state, current)
    if retry:
        if retry not in state:
            raise ValueError("unknown job")
        state[retry].update(
            status="pending",
            attempts=0,
            next=current.isoformat(),
            deadline=None,
            notified=False,
        )
    for key, job in sorted(state.items()):
        if job["status"] == "running":
            job.update(
                status="pending",
                error="interrupted",
                next=(now() + timedelta(minutes=10)).isoformat(),
            )
        if job["status"] == "pending":
            expired = job["deadline"] and now() >= datetime.fromisoformat(
                job["deadline"]
            )
            exhausted = (job["kind"] != "closeout" or not job["deadline"]) and job[
                "attempts"
            ] >= 6
            if expired or exhausted:
                job.update(status="failed", error=job.get("error", "deadline"))
            elif now() >= datetime.fromisoformat(job["next"]):
                job.update(status="running", attempts=job["attempts"] + 1)
                save(state_path, state)
                try:
                    attempt(key, job)
                except Exception as error:
                    # Only our fixed stage codes are safe for mail; no external exception text.
                    job["error"] = (
                        str(error)
                        if type(error) is RuntimeError
                        else type(error).__name__
                    )
                    job["status"] = "pending"
                    job["next"] = (now() + timedelta(minutes=10)).isoformat()
                    if (
                        (job["kind"] != "closeout" or not job["deadline"])
                        and job["attempts"] >= 6
                    ) or (
                        job["deadline"]
                        and now() >= datetime.fromisoformat(job["deadline"])
                    ):
                        job["status"] = "failed"
                else:
                    job["status"] = "complete"
        save(state_path, state)
        if job["status"] == "failed":
            alert(key, job)
    summary = {key: job for key, job in state.items() if job["kind"] == "closeout"}
    save(DATA / "closeout.json", summary)


def main():
    global LOCK_FD
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retry", help="人工续跑指定任务（保留日期、检查点，解除凌晨截止限制）"
    )
    parser.add_argument("--status", action="store_true", help="只读查看任务状态")
    parser.add_argument("--upload-week", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.chdir(ROOT)
    load_dotenv(ROOT / "config" / ".env", quiet=True)
    os.environ["TZ"] = "Asia/Shanghai"
    os.environ["PYTHONUNBUFFERED"] = "1"
    if args.upload_week:
        datetime.strptime(args.upload_week, "%Y%m%d")
        upload_week(DATA / "weeks" / args.upload_week)
        return
    if args.status:
        print(json.dumps(load(DATA / "jobs.json", {}), ensure_ascii=False, indent=2))
        return
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        LOCK_FD = lock.fileno()
        tick(args.retry)


if __name__ == "__main__":
    main()
