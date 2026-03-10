#!/usr/bin/env python3
"""Super file compression utility.

Creates tar archives with high-compression algorithms.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SUPPORTED_METHODS = ("auto", "zstd", "xz", "gzip")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Super compression for files/folders into tar archives"
    )
    parser.add_argument("inputs", nargs="+", help="File(s) or folder(s) to compress")
    parser.add_argument("-o", "--output", required=True, help="Output archive path")
    parser.add_argument(
        "-l",
        "--level",
        type=int,
        default=9,
        help="Compression level (1-22 for zstd, 0-9 for gzip/xz; default: 9)",
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=SUPPORTED_METHODS,
        default="auto",
        help="Compression method: auto, zstd, xz, gzip (default: auto)",
    )
    return parser.parse_args()


def resolve_method(method: str) -> str:
    if method != "auto":
        return method
    if shutil.which("zstd"):
        return "zstd"
    if shutil.which("xz"):
        return "xz"
    return "gzip"


def validate(args: argparse.Namespace, method: str) -> None:
    missing = [item for item in args.inputs if not Path(item).exists()]
    if missing:
        raise FileNotFoundError(f"Input path(s) not found: {', '.join(missing)}")

    if method == "zstd" and not (1 <= args.level <= 22):
        raise ValueError("For zstd, compression level must be between 1 and 22.")
    if method in {"xz", "gzip"} and not (0 <= args.level <= 9):
        raise ValueError("For xz/gzip, compression level must be between 0 and 9.")

    if method == "zstd" and shutil.which("zstd") is None:
        raise EnvironmentError("'zstd' is not available in PATH.")


def normalize_output(output: str, method: str) -> str:
    suffix_map = {
        "zstd": ".tar.zst",
        "xz": ".tar.xz",
        "gzip": ".tar.gz",
    }
    ext = suffix_map[method]
    return output if output.endswith(ext) else f"{output}{ext}"


def make_archive(inputs: list[str], output: str, method: str, level: int) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if method == "zstd":
        cmd = ["tar", f"--use-compress-program=zstd -{level} --long=31", "-cf", output, *inputs]
    elif method == "xz":
        cmd = ["tar", f"-I", f"xz -{level}", "-cf", output, *inputs]
    else:
        cmd = ["tar", f"-I", f"gzip -{level}", "-cf", output, *inputs]

    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()
    method = resolve_method(args.method)
    output = normalize_output(args.output, method)

    try:
        validate(args, method)
        make_archive(args.inputs, output, method, args.level)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Archive created: {shlex.quote(output)} (method: {method})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
