#!/usr/bin/env python3
"""Normalize a meme animation with ImageMagick, preserving frame timing."""

import argparse
import re
import subprocess
import tempfile
from pathlib import Path


def magick(*args):
    return subprocess.check_output(["magick", *map(str, args)], text=True).strip()


def process(source, output, background=None, fuzz=10):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError("输出不能覆盖源文件")
    if output.suffix.lower() != ".webp":
        raise ValueError("输出必须为 .webp")
    delays = magick("identify", "-format", "%T ", source).split()
    with tempfile.TemporaryDirectory(prefix="meme-") as work:
        work = Path(work)
        magick(source, "-coalesce", work / "source-%05d.png")
        frames = sorted(work.glob("source-*.png"))
        if len(frames) != len(delays):
            raise ValueError("源文件帧数与 delay 数量不一致")
        if background is None and all(
            magick("identify", "-format", "%[opaque]", frame).lower() == "true"
            for frame in frames
        ):
            raise ValueError(
                "源文件无透明背景；检查素材后使用 --background 显式指定背景颜色"
            )
        boxes = []
        for frame in frames:
            if background is not None:
                magick(
                    frame,
                    "-alpha",
                    "on",
                    "-bordercolor",
                    background,
                    "-border",
                    "1",
                    "-fuzz",
                    f"{fuzz}%",
                    "-fill",
                    "none",
                    "-draw",
                    "alpha 0,0 floodfill",
                    "-shave",
                    "1x1",
                    frame,
                )
            geometry = magick(
                frame,
                "-alpha",
                "extract",
                "-threshold",
                "0",
                "-format",
                "%@",
                "info:",
            )
            match = re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", geometry)
            if not match:
                raise ValueError(f"无法确定前景边界：{geometry}")
            width, height, x, y = map(int, match.groups())
            boxes.append((x, y, x + width, y + height))
        x, y = min(b[0] for b in boxes), min(b[1] for b in boxes)
        width = max(b[2] for b in boxes) - x
        height = max(b[3] for b in boxes) - y
        animation = []
        for index, (frame, delay) in enumerate(zip(frames, delays)):
            final = work / f"final-{index:05d}.png"
            magick(
                frame,
                "-crop",
                f"{width}x{height}+{x}+{y}",
                "+repage",
                "-resize",
                "184x184",
                "-background",
                "none",
                "-gravity",
                "south",
                "-extent",
                "200x192",
                "-gravity",
                "north",
                "-extent",
                "200x200",
                final,
            )
            animation.extend(["-delay", delay, str(final)])
        candidate = work / "result.webp"
        magick(*animation, "-loop", "0", "-define", "webp:lossless=true", candidate)
        rows = [
            row.split()
            for row in magick(
                candidate,
                "-coalesce",
                "-format",
                "%w %h %T %[channels]\n",
                "info:",
            ).splitlines()
        ]
        if not rows or any(
            row[:2] != ["200", "200"] or "a" not in row[3] for row in rows
        ):
            raise ValueError("输出画布或透明通道校验失败")
        if sum(int(row[2]) for row in rows) != sum(map(int, delays)):
            raise ValueError("输出动画总时长与源文件不一致")
        # Replace the derived file only after conversion and validation succeed.
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=output.parent, suffix=".webp", delete=False
        ) as handle:
            staging = Path(handle.name)
            try:
                handle.write(candidate.read_bytes())
                handle.close()
                staging.replace(output)
            finally:
                staging.unlink(missing_ok=True)
    return len(rows), sum(map(int, delays)) * 10


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="原始 GIF 或其他动画文件")
    parser.add_argument(
        "--output", type=Path, help="默认输出到源文件所在 originals/ 的上一级"
    )
    parser.add_argument("--background", help="仅删除从外缘连通的背景，例如 '#000000'")
    parser.add_argument(
        "--fuzz", type=float, default=10, help="去背景颜色容差百分比，默认 10"
    )
    args = parser.parse_args()
    if not 0 <= args.fuzz <= 100:
        parser.error("--fuzz 必须在 0 到 100 之间")
    if args.output is None and args.source.parent.name != "originals":
        parser.error("源文件不在 originals/ 中时必须指定 --output")
    output = args.output or args.source.parent.parent / (args.source.stem + ".webp")
    try:
        frames, duration = process(args.source, output, args.background, args.fuzz)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"处理失败：{error}\n")
    print(f"{output}: {frames} encoded frames, {duration} ms, 200×200, alpha")


if __name__ == "__main__":
    main()
