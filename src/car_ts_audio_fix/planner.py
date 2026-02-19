from __future__ import annotations

from pathlib import Path

from .model import AudioCodec, FileInfo, Options, Plan

COMPAT_CODECS = {"mp2", "ac3", "aac"}
DEFAULT_BITRATES = {
    AudioCodec.MP2: "192k",
    AudioCodec.AC3: "384k",
    AudioCodec.AAC: "192k",
}


def build_plans(file_info: FileInfo, options: Options) -> list[Plan]:
    if options.compat_test:
        return _build_compat_test_plans(file_info, options)
    return [_build_single_plan(file_info, options, options.audio_codec)]


def _build_compat_test_plans(file_info: FileInfo, options: Options) -> list[Plan]:
    plans: list[Plan] = []
    for codec in (AudioCodec.MP2, AudioCodec.AC3, AudioCodec.AAC):
        outdir = options.outdir or file_info.path.parent
        output_path = outdir / f"{file_info.path.stem}.test_{codec.value}.ts"
        p = _build_single_plan(file_info, options, codec, output_path=output_path)
        p.duration_seconds = options.test_seconds
        p.aac_latm = options.aac_latm if codec == AudioCodec.AAC else False
        plans.append(p)
    return plans


def _build_single_plan(
    file_info: FileInfo,
    options: Options,
    codec: AudioCodec,
    output_path: Path | None = None,
) -> Plan:
    audio_streams = file_info.audio_streams
    video_streams = file_info.video_streams
    if not audio_streams:
        raise ValueError("Входной файл не содержит аудиодорожек")
    if not video_streams:
        raise ValueError("Входной файл не содержит видеодорожек")

    selected_audio_idx = options.audio_track if options.audio_track is not None else 0
    if selected_audio_idx >= len(audio_streams):
        raise ValueError(f"Запрошенная аудиодорожка {selected_audio_idx} отсутствует")

    selected_audios = audio_streams if options.all_audio else [audio_streams[selected_audio_idx]]
    maps = [f"0:{video_streams[0].index}"] + [f"0:{a.index}" for a in selected_audios]

    if options.keep_original_audio:
        for a in audio_streams:
            if f"0:{a.index}" not in maps:
                maps.append(f"0:{a.index}")

    outdir = options.outdir or file_info.path.parent
    output_path = output_path or outdir / f"{file_info.path.stem}{options.suffix}.ts"

    plan = Plan(
        input_path=file_info.path,
        output_path=output_path,
        maps=maps,
        audio_codec=codec,
        audio_bitrate=options.audio_bitrate or DEFAULT_BITRATES[codec],
        sample_rate=options.sr,
        channels=options.ac,
        video_copy=not options.safe_video,
        safe_video=options.safe_video,
        safe_preset=options.safe_preset,
        safe_crf=options.safe_crf,
        safe_fps=options.safe_fps,
        safe_gop=options.safe_gop or options.safe_fps * 2,
        keep_original_audio=options.keep_original_audio,
        aac_latm=options.aac_latm if codec == AudioCodec.AAC else False,
    )

    if options.skip_compatible and _is_compatible(file_info, options, selected_audios):
        plan.skip = True
        plan.reason = "already compatible"

    return plan


def _is_compatible(file_info: FileInfo, options: Options, selected_audios) -> bool:
    if file_info.path.suffix.lower() != ".ts":
        return False
    for audio in selected_audios:
        if (audio.codec_name or "").lower() not in COMPAT_CODECS:
            return False
        if options.sr and audio.sample_rate and int(audio.sample_rate) != int(options.sr):
            return False
        if options.ac and audio.channels and int(audio.channels) != int(options.ac):
            return False
    return True
