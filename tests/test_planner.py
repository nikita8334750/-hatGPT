from pathlib import Path

from car_ts_audio_fix.model import AudioCodec, FileInfo, Options, StreamInfo
from car_ts_audio_fix.planner import build_plans


def mk_file(path: str, streams: list[StreamInfo]) -> FileInfo:
    return FileInfo(path=Path(path), streams=streams)


def test_mkv_dts_to_mp2_default_plan() -> None:
    info = mk_file(
        "movie.mkv",
        [
            StreamInfo(index=0, codec_type="video", codec_name="h264"),
            StreamInfo(index=1, codec_type="audio", codec_name="dts", channels=6, sample_rate=48000),
        ],
    )
    plan = build_plans(info, Options())[0]
    assert plan.output_path.suffix == ".ts"
    assert plan.audio_codec == AudioCodec.MP2
    assert plan.channels == 2
    assert plan.maps == ["0:0", "0:1"]


def test_skip_compatible_ts_mp2() -> None:
    info = mk_file(
        "ready.ts",
        [
            StreamInfo(index=0, codec_type="video", codec_name="mpeg2video"),
            StreamInfo(index=1, codec_type="audio", codec_name="mp2", channels=2, sample_rate=48000),
        ],
    )
    options = Options(skip_compatible=True)
    plan = build_plans(info, options)[0]
    assert plan.skip is True


def test_audio_track_selection_default_and_custom() -> None:
    info = mk_file(
        "multi.mkv",
        [
            StreamInfo(index=0, codec_type="video", codec_name="h264"),
            StreamInfo(index=1, codec_type="audio", codec_name="dts", channels=6, sample_rate=48000),
            StreamInfo(index=2, codec_type="audio", codec_name="aac", channels=2, sample_rate=48000),
        ],
    )
    default_plan = build_plans(info, Options())[0]
    custom_plan = build_plans(info, Options(audio_track=1))[0]

    assert default_plan.maps == ["0:0", "0:1"]
    assert custom_plan.maps == ["0:0", "0:2"]


def test_compat_test_three_plans_with_duration_and_aac_latm() -> None:
    info = mk_file(
        "clip.mp4",
        [
            StreamInfo(index=0, codec_type="video", codec_name="h264"),
            StreamInfo(index=1, codec_type="audio", codec_name="aac", channels=2, sample_rate=44100),
        ],
    )
    opts = Options(compat_test=True, test_seconds=15, aac_latm=True)
    plans = build_plans(info, opts)
    assert [p.audio_codec for p in plans] == [AudioCodec.MP2, AudioCodec.AC3, AudioCodec.AAC]
    assert all(p.duration_seconds == 15 for p in plans)
    assert plans[2].aac_latm is True
    assert plans[0].aac_latm is False
