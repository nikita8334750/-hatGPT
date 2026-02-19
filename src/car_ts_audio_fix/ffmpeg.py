from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .model import FileInfo, Plan, StreamInfo


def find_binaries() -> tuple[str | None, str | None]:
    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def probe_file(ffprobe_bin: str, path: Path) -> FileInfo:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    streams = []
    for raw in data.get("streams", []):
        streams.append(
            StreamInfo(
                index=int(raw["index"]),
                codec_type=raw.get("codec_type", ""),
                codec_name=raw.get("codec_name"),
                channels=raw.get("channels"),
                sample_rate=int(raw["sample_rate"]) if raw.get("sample_rate") else None,
            )
        )
    return FileInfo(path=path, streams=streams, format_name=data.get("format", {}).get("format_name"))


def build_ffmpeg_argv(ffmpeg_bin: str, plan: Plan, overwrite: bool = False) -> list[str]:
    cmd: list[str] = [ffmpeg_bin, "-hide_banner", "-loglevel", "error"]
    cmd.append("-y" if overwrite else "-n")
    if plan.duration_seconds:
        cmd += ["-t", str(plan.duration_seconds)]
    cmd += ["-i", str(plan.input_path)]

    for m in plan.maps:
        cmd += ["-map", m]

    if plan.safe_video:
        cmd += [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "baseline",
            "-level:v",
            "3.1",
            "-preset",
            plan.safe_preset,
            "-crf",
            str(plan.safe_crf),
            "-r",
            str(plan.safe_fps),
            "-g",
            str(plan.safe_gop),
        ]
    else:
        cmd += ["-c:v", "copy"]

    cmd += ["-c:a", plan.audio_codec.value, "-b:a", plan.audio_bitrate, "-ar", str(plan.sample_rate), "-ac", str(plan.channels)]

    if plan.keep_original_audio:
        # Preserve any additional audio tracks that were explicitly mapped beyond selected ones.
        cmd += ["-c:a:1", "copy"]

    if plan.aac_latm:
        cmd += ["-mpegts_flags", "+latm"]

    cmd += ["-f", "mpegts", str(plan.output_path)]
    return cmd


def run_ffmpeg(argv: list[str]) -> None:
    subprocess.run(argv, check=True)
