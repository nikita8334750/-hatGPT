from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .ffmpeg import build_ffmpeg_argv, find_binaries, probe_file, run_ffmpeg
from .model import AudioCodec, JobResult, Options
from .planner import build_plans
from .utils import collect_inputs, setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="car-ts-audio-fix")
    p.add_argument("input", type=Path)
    p.add_argument("--suffix", default=".car")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--outdir", type=Path)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true")

    p.add_argument("--audio-codec", choices=[c.value for c in AudioCodec], default="mp2")
    p.add_argument("--audio-bitrate")
    p.add_argument("--sr", type=int, default=48000)
    p.add_argument("--ac", type=int, default=2)
    p.add_argument("--audio-track", type=int)
    p.add_argument("--all-audio", action="store_true")
    p.add_argument("--keep-original-audio", action="store_true")
    p.add_argument("--aac-latm", action="store_true")
    p.add_argument("--skip-compatible", action="store_true")

    p.add_argument("--compat-test", action="store_true")
    p.add_argument("--test-seconds", type=int, default=20)

    p.add_argument("--safe-video", action="store_true")
    p.add_argument("--safe-preset", default="veryfast")
    p.add_argument("--safe-crf", type=int, default=23)
    p.add_argument("--safe-fps", type=int, default=30)
    p.add_argument("--safe-gop", type=int)
    return p.parse_args(argv)


def ns_to_options(ns: argparse.Namespace) -> Options:
    return Options(
        suffix=ns.suffix,
        outdir=ns.outdir,
        audio_codec=AudioCodec(ns.audio_codec),
        audio_bitrate=ns.audio_bitrate,
        sr=ns.sr,
        ac=ns.ac,
        audio_track=ns.audio_track,
        all_audio=ns.all_audio,
        keep_original_audio=ns.keep_original_audio,
        aac_latm=ns.aac_latm,
        skip_compatible=ns.skip_compatible,
        compat_test=ns.compat_test,
        test_seconds=ns.test_seconds,
        safe_video=ns.safe_video,
        safe_preset=ns.safe_preset,
        safe_crf=ns.safe_crf,
        safe_fps=ns.safe_fps,
        safe_gop=ns.safe_gop,
        dry_run=ns.dry_run,
        overwrite=ns.overwrite,
    )


def process_file(path: Path, ffmpeg_bin: str, ffprobe_bin: str, options: Options) -> JobResult:
    try:
        info = probe_file(ffprobe_bin, path)
        plans = build_plans(info, options)
        for plan in plans:
            if plan.skip:
                logging.info("SKIP %s (%s)", path, plan.reason)
                continue
            plan.output_path.parent.mkdir(parents=True, exist_ok=True)
            argv = build_ffmpeg_argv(ffmpeg_bin, plan, overwrite=options.overwrite)
            if options.dry_run:
                logging.info("DRY-RUN: %s", argv)
            else:
                run_ffmpeg(argv)
                logging.info("OK: %s -> %s", path, plan.output_path)
        return JobResult(input_path=path, plans=plans, skipped=all(p.skip for p in plans))
    except Exception as exc:  # noqa: BLE001
        logging.error("FAIL %s: %s", path, exc)
        return JobResult(input_path=path, ok=False, error=str(exc))


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    ns = parse_args(argv)
    options = ns_to_options(ns)

    ffmpeg_bin, ffprobe_bin = find_binaries()
    if not ffmpeg_bin or not ffprobe_bin:
        logging.error("ffmpeg и/или ffprobe не найдены в PATH")
        return 2

    inputs = collect_inputs(ns.input, ns.recursive)
    if not inputs:
        logging.warning("Нет входных файлов для обработки")
        return 0

    results: list[JobResult] = []
    with ThreadPoolExecutor(max_workers=max(1, ns.jobs)) as ex:
        futures = [ex.submit(process_file, p, ffmpeg_bin, ffprobe_bin, options) for p in inputs]
        for f in as_completed(futures):
            results.append(f.result())

    has_errors = any(not r.ok for r in results)
    return 3 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
