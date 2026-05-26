#!/usr/bin/env python3
"""Run AlmondTTS on every chapter file and produce MP3s.

Usage:
    python run_tts.py                            # all chapters, default engine (xtts)
    python run_tts.py -e kokoro                  # all chapters, kokoro engine
    python run_tts.py -e voxtral ch01 ch02       # specific chapters, voxtral engine

Output: output/audio/<chapter>.mp3
"""

import os
import sys
import glob
import argparse
import subprocess

CHAPTERS_DIR  = "./output/chapters"
AUDIO_DIR     = "./output/audio"
ALMOND_PYTHON = os.path.expanduser("~/Projects/AlmondTTS/venv/bin/python")
ALMOND_SCRIPT = os.path.expanduser("~/Projects/AlmondTTS/backend/almond_tts_lib.py")
FORMAT        = "mp3"


def run_chapter(txt_path, engine, language):
    base = os.path.splitext(os.path.basename(txt_path))[0]
    cmd = [
        ALMOND_PYTHON, ALMOND_SCRIPT,
        txt_path,
        "-e", engine,
        "-l", language,
        "-f", FORMAT,
        "-o", base,
        "-d", os.path.abspath(AUDIO_DIR),
    ]
    print(f"\n>>> {base}")
    print(" ".join(cmd))
    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"ERROR: {base} failed with exit code {result.returncode}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Run AlmondTTS on chapter files.")
    parser.add_argument(
        "-e", "--engine",
        default="xtts",
        choices=["xtts", "kokoro", "piper", "voxtral"],
        help="TTS engine to use (default: xtts)",
    )
    parser.add_argument(
        "-l", "--language",
        default="en",
        help="Language code (default: en)",
    )
    parser.add_argument(
        "chapters",
        nargs="*",
        help="Chapter prefixes to process, e.g. ch01 ch02 (default: all)",
    )
    args = parser.parse_args()

    os.makedirs(AUDIO_DIR, exist_ok=True)

    all_chapters = sorted(glob.glob(os.path.join(CHAPTERS_DIR, "ch*.txt")))
    if not all_chapters:
        print(f"No chapter files found in {CHAPTERS_DIR}/")
        print("Run md_to_chapters.py first.")
        sys.exit(1)

    if args.chapters:
        all_chapters = [
            p for p in all_chapters
            if any(os.path.basename(p).startswith(f) for f in args.chapters)
        ]
        if not all_chapters:
            print(f"No chapters matched: {args.chapters}")
            sys.exit(1)

    print(f"Engine: {args.engine}")
    print(f"Processing {len(all_chapters)} chapter(s) → {AUDIO_DIR}/")

    failed = []
    for path in all_chapters:
        ok = run_chapter(path, args.engine, args.language)
        if not ok:
            failed.append(os.path.basename(path))

    print("\n--- Done ---")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"{len(all_chapters)} MP3(s) written to {AUDIO_DIR}/")


if __name__ == "__main__":
    main()
