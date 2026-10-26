# /// script
# requires-python = ">=3.11"
# dependencies = ["faster-whisper>=1.1", "requests>=2.32"]
# ///
"""Cheap voice-over dub: whisper -> google translate -> old ElevenLabs voices -> ffmpeg.

uv run dub/dub.py INPUT [--to ru] [--out DIR]
Needs ELEVENLABS_API_KEY for the voice. Without it, writes only the translated .srt.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

ELEVEN = "https://api.elevenlabs.io/v1"
VOICE = "pNInz6obpgDQGcFmaJgB"  # Adam, the classic 2023 voice
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def run(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def duration(path: Path) -> float:
    out = run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path))
    return float(json.loads(out)["format"]["duration"])


def transcribe(audio: Path, model: str) -> tuple[str, list[dict]]:
    from faster_whisper import WhisperModel

    import numpy as np

    # Decode with ffmpeg ourselves: faster-whisper's own PyAV decoding breaks across av releases.
    pcm = subprocess.run(
        ["ffmpeg", "-i", str(audio), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], check=True, capture_output=True
    ).stdout
    samples = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    whisper = WhisperModel(model, device="cpu", compute_type="int8")
    segments, info = whisper.transcribe(samples, vad_filter=True)
    return info.language, [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments if s.text.strip()]


def translate(text: str, target: str) -> str:
    r = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text},
        timeout=30,
    )
    r.raise_for_status()
    return "".join(part[0] for part in r.json()[0] if part[0])


def speak(text: str, target: str, key: str, dest: Path) -> None:
    model = "eleven_monolingual_v1" if target == "en" else "eleven_multilingual_v1"
    r = requests.post(
        f"{ELEVEN}/text-to-speech/{VOICE}",
        headers={"xi-api-key": key},
        json={"text": text, "model_id": model, "voice_settings": {"stability": 0.3, "similarity_boost": 0.5}},
        timeout=120,
    )
    if r.status_code != 200:
        sys.exit(f"elevenlabs {r.status_code}: {r.text[:300]}")
    dest.write_bytes(r.content)


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def write_srt(segments: list[dict], dest: Path) -> None:
    lines = [f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['dub']}\n" for i, s in enumerate(segments, 1)]
    dest.write_text("\n".join(lines))


def fit(clip: Path, slot: float, dest: Path) -> float:
    """Speed the clip up to fit its slot, at most 1.8x. Returns the new length."""
    length = duration(clip)
    speed = min(max(length / slot, 1.0), 1.8) if slot > 0 else 1.0
    run("ffmpeg", "-y", "-i", str(clip), "-filter:a", f"atempo={speed:.3f}", "-ar", "44100", "-ac", "1", str(dest))
    return length / speed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--to", default=None, help="target language, default ru (en if the source is Russian)")
    ap.add_argument("--out", type=Path, default=Path("/mnt/user-data/outputs"))
    ap.add_argument("--whisper", default="small")
    args = ap.parse_args()

    src: Path = args.input.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    tmp = Path(tempfile.mkdtemp(prefix="dub-"))

    audio = tmp / "orig.wav"
    run("ffmpeg", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(audio))
    lang, segments = transcribe(audio, args.whisper)
    target = args.to or ("en" if lang == "ru" else "ru")
    print(f"source {lang}, target {target}, {len(segments)} segments", file=sys.stderr)

    for s in segments:
        s["dub"] = translate(s["text"], target)
    srt = args.out / f"{src.stem}.{target}.srt"
    write_srt(segments, srt)
    print(srt)
    if not key:
        sys.exit("ELEVENLABS_API_KEY is not set, wrote only the subtitles")

    # One voice over the ducked original, each line no earlier than the previous one ends.
    inputs, filters, cursor = ["-i", str(src)], [], 0.0
    for i, s in enumerate(segments):
        raw, clip = tmp / f"{i}.mp3", tmp / f"{i}.wav"
        speak(s["dub"], target, key, raw)
        nxt = segments[i + 1]["start"] if i + 1 < len(segments) else s["end"] + 2
        start = max(s["start"], cursor)
        cursor = start + fit(raw, nxt - start, clip)
        inputs += ["-i", str(clip)]
        filters.append(f"[{i + 1}:a]adelay={round(start * 1000)}:all=1[d{i}]")
    voices = "".join(f"[d{i}]" for i in range(len(segments)))
    filters.append(f"[0:a]volume=0.2[bg];[bg]{voices}amix=inputs={len(segments) + 1}:normalize=0:duration=first[out]")

    is_video = src.suffix.lower() in VIDEO_EXT
    dest = args.out / f"{src.stem}.dub.{target}.{'mp4' if is_video else 'mp3'}"
    codec = ["-map", "0:v", "-c:v", "copy", "-c:a", "aac"] if is_video else ["-c:a", "libmp3lame", "-q:a", "3"]
    run("ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", *codec, str(dest))
    print(dest)


if __name__ == "__main__":
    main()
