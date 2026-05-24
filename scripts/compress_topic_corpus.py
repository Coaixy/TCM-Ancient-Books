#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "processed" / "topics"
TARGET_SUFFIXES = {".jsonl", ".json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="压缩 processed/topics 下的 JSONL / JSON 数据文件。")
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="待压缩目录，默认是仓库内的 processed/topics",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="如果目标压缩包已存在则覆盖",
    )
    return parser.parse_args()


def iter_targets(input_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix in TARGET_SUFFIXES
    )


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def compress_file(source_path: Path, force: bool) -> str:
    archive_path = source_path.with_name(f"{source_path.name}.gz")
    if archive_path.exists() and not force:
        return f"skip  {display_path(source_path)} -> {display_path(archive_path)}"

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with source_path.open("rb") as source, gzip.open(archive_path, "wb") as target:
        shutil.copyfileobj(source, target)
    return f"done  {display_path(source_path)} -> {display_path(archive_path)}"


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"目录不存在：{input_dir}")

    targets = iter_targets(input_dir)
    if not targets:
        print(f"未找到可压缩的 .jsonl / .json 文件：{display_path(input_dir)}")
        return 0

    compressed = 0
    skipped = 0
    for source_path in targets:
        result = compress_file(source_path, force=args.force)
        print(result)
        if result.startswith("done"):
            compressed += 1
        else:
            skipped += 1

    print(f"完成：压缩 {compressed} 个，跳过 {skipped} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
