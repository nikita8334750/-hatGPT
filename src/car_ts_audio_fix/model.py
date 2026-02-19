from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AudioCodec(str, Enum):
    MP2 = "mp2"
    AC3 = "ac3"
    AAC = "aac"


@dataclass(slots=True)
class StreamInfo:
    index: int
    codec_type: str
    codec_name: str | None = None
    channels: int | None = None
    sample_rate: int | None = None


@dataclass(slots=True)
class FileInfo:
    path: Path
    streams: list[StreamInfo]
    format_name: str | None = None

    @property
    def video_streams(self) -> list[StreamInfo]:
        return [s for s in self.streams if s.codec_type == "video"]

    @property
    def audio_streams(self) -> list[StreamInfo]:
        return [s for s in self.streams if s.codec_type == "audio"]


@dataclass(slots=True)
class Options:
    suffix: str = ".car"
    outdir: Path | None = None
    audio_codec: AudioCodec = AudioCodec.MP2
    audio_bitrate: str | None = None
    sr: int = 48000
    ac: int = 2
    audio_track: int | None = None
    all_audio: bool = False
    keep_original_audio: bool = False
    aac_latm: bool = False
    skip_compatible: bool = False
    compat_test: bool = False
    test_seconds: int = 20
    safe_video: bool = False
    safe_preset: str = "veryfast"
    safe_crf: int = 23
    safe_fps: int = 30
    safe_gop: int | None = None
    dry_run: bool = False
    overwrite: bool = False


@dataclass(slots=True)
class Plan:
    input_path: Path
    output_path: Path
    maps: list[str]
    audio_codec: AudioCodec
    audio_bitrate: str
    sample_rate: int
    channels: int
    video_copy: bool
    safe_video: bool
    safe_preset: str
    safe_crf: int
    safe_fps: int
    safe_gop: int
    keep_original_audio: bool = False
    duration_seconds: int | None = None
    aac_latm: bool = False
    skip: bool = False
    reason: str | None = None


@dataclass(slots=True)
class JobResult:
    input_path: Path
    plans: list[Plan] = field(default_factory=list)
    ok: bool = True
    skipped: bool = False
    error: str | None = None
