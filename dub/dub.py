# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.32"]
# ///
"""Dub audio or video with the ElevenLabs Dubbing API (dubbing_v1).

uv run dub/dub.py INPUT [--to ru] [--from auto] [--speakers N] [--out DIR]
Needs ELEVENLABS_API_KEY with the dubbing permission.
"""

import argparse
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

API = "https://api.elevenlabs.io/v1/dubbing"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--to", default="ru", help="target language code")
    ap.add_argument("--from", dest="source", default="auto", help="source language code")
    ap.add_argument("--speakers", type=int, default=0, help="number of speakers, 0 lets ElevenLabs detect")
    ap.add_argument("--out", type=Path, default=Path("/mnt/user-data/outputs"))
    args = ap.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY is not set")
    headers = {"xi-api-key": key}
    src: Path = args.input.resolve()
    mime = mimetypes.guess_type(src.name)[0] or "video/mp4"

    with src.open("rb") as f:
        r = requests.post(
            API,
            headers=headers,
            files={"file": (src.name, f, mime)},
            # Free plan only allows watermarked video dubs.
            data={"target_lang": args.to, "source_lang": args.source, "watermark": "true", "num_speakers": args.speakers},
            timeout=600,
        )
    if not r.ok:
        sys.exit(f"elevenlabs {r.status_code}: {r.text[:300]}")
    job = r.json()["dubbing_id"]
    print(f"dubbing {job}, about {r.json().get('expected_duration_sec', 0):.0f}s", file=sys.stderr)

    while True:
        status = requests.get(f"{API}/{job}", headers=headers, timeout=60).json()
        if status["status"] == "dubbed":
            break
        if status["status"] == "failed" or status.get("error"):
            sys.exit(f"dubbing failed: {status.get('error')}")
        time.sleep(10)

    r = requests.get(f"{API}/{job}/audio/{args.to}", headers=headers, timeout=600)
    r.raise_for_status()
    ext = mimetypes.guess_extension(r.headers.get("content-type", "").split(";")[0]) or src.suffix
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / f"{src.stem}.dub.{args.to}{ext}"
    dest.write_bytes(r.content)
    print(dest)


if __name__ == "__main__":
    main()
