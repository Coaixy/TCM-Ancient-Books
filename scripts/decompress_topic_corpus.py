#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "processed" / "topics"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="解压 processed/topics 下的 .gz 数据文件。")
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="待解压目录，默认是仓库内的 processed/topics",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="如果目标文件已存在则覆盖",
    )
    return parser.parse_args()


def iter_archives(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.rglob("*.gz") if path.is_file())


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def decompress_file(archive_path: Path, force: bool) -> str:
    output_path = archive_path.with_suffix("")
    if output_path.exists() and not force:
        return f"skip  {display_path(archive_path)} -> {display_path(output_path)}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(archive_path, "rb") as source, output_path.open("wb") as target:
        shutil.copyfileobj(source, target)
    return f"done  {display_path(archive_path)} -> {display_path(output_path)}"


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"目录不存在：{input_dir}")

    archives = iter_archives(input_dir)
    if not archives:
        print(f"未找到 .gz 文件：{display_path(input_dir)}")
        return 0

    decompressed = 0
    skipped = 0
    for archive_path in archives:
        result = decompress_file(archive_path, force=args.force)
        print(result)
        if result.startswith("done"):
            decompressed += 1
        else:
            skipped += 1

    print(f"完成：解压 {decompressed} 个，跳过 {skipped} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
