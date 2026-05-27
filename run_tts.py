#!/usr/bin/env python3
"""Run AlmondTTS on every chapter file and produce MP3s.

Usage:
    python run_tts.py                            # all chapters, default engine (xtts)
    python run_tts.py -e kokoro                  # all chapters, kokoro engine
    python run_tts.py -e voxtral ch01 ch02       # specific chapters, voxtral engine

Output: output/audio/<chapter>.mp3
         output/audio/<chapter>.json   (validation log)
"""

import os
import re
import subprocess
import sys
import glob
import argparse
from datetime import datetime, timezone

CHAPTERS_DIR  = "./output/chapters"
AUDIO_DIR     = "./output/audio"
LOG_FILE      = "./output/audio/tts.log"
ALMOND_PYTHON = os.path.expanduser("~/Projects/AlmondTTS/venv/bin/python")
ALMOND_SCRIPT = os.path.expanduser("~/Projects/AlmondTTS/backend/almond_tts_lib.py")
FORMAT        = "mp3"
XTTS_MAX_DURATION = "30"


# ---------------------------------------------------------------------------
# Audio duration helpers
# ---------------------------------------------------------------------------

def audio_duration_sox(path):
    """Return duration in seconds using soxi, or None on failure."""
    try:
        result = subprocess.run(
            ["soxi", "-D", path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except FileNotFoundError:
        pass
    return None


def audio_duration_ffprobe(path):
    """Return duration in seconds using ffprobe, or None on failure."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet",
             "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except FileNotFoundError:
        pass
    return None


def get_audio_duration(path):
    return audio_duration_sox(path) or audio_duration_ffprobe(path)


# ---------------------------------------------------------------------------
# Log-line parsers (AlmondTTS stdout)
# ---------------------------------------------------------------------------

# [2026-05-26 13:45:01] [42/153] ID 017 | 26.3s audio | some text…
SEGMENT_RE = re.compile(
    r"\[(\d+)/(\d+)\].*?ID\s+(\d+)\s*\|.*?(\d+(?:\.\d+)?)s audio"
)

# [2026-05-26 13:45:01] [42/153] Segment 43 [ID: 017]: ERROR - …
ERROR_RE = re.compile(
    r"\[(\d+)/(\d+)\].*?Segment.*?ID.*?(\d+).*?ERROR\s*[-–]\s*(.+)"
)

# duration guard failures produce "exceeded duration limit" messages
DURATION_EXCEEDED_RE = re.compile(r"exceeded duration limit")


def parse_almond_output(lines):
    """Extract segment stats from AlmondTTS log lines."""
    total_segments = 0
    completed_segments = 0
    failed_segments = []
    segment_durations = []   # list of (segment_id, duration_s)
    duration_limit_hits = 0

    for line in lines:
        m = SEGMENT_RE.search(line)
        if m:
            completed_segments = int(m.group(1))
            total_segments     = int(m.group(2))
            seg_id             = int(m.group(3))
            seg_duration       = float(m.group(4))
            segment_durations.append((seg_id, seg_duration))

        m = ERROR_RE.search(line)
        if m:
            failed_segments.append({
                "segment_id": int(m.group(3)),
                "error": m.group(4).strip()
            })

        if DURATION_EXCEEDED_RE.search(line):
            duration_limit_hits += 1

    durations = [d for _, d in segment_durations]
    mean_dur  = sum(durations) / len(durations) if durations else 0

    # Outlier: any segment > 3× the mean is a hallucination candidate
    outliers = [
        {"segment_id": sid, "duration_s": dur, "ratio": round(dur / mean_dur, 1)}
        for sid, dur in segment_durations
        if mean_dur > 0 and dur > mean_dur * 3
    ]

    return {
        "total_segments":      total_segments,
        "completed_segments":  completed_segments,
        "failed_segments":     failed_segments,
        "failed_count":        len(failed_segments),
        "duration_limit_hits": duration_limit_hits,
        "tts_audio_total_s":   round(sum(durations), 2),
        "tts_audio_mean_s":    round(mean_dur, 2),
        "outlier_segments":    outliers,
        "outlier_count":       len(outliers),
    }


def build_almond_command(txt_path, engine, language, output_base, output_dir):
    cmd = [
        ALMOND_PYTHON, ALMOND_SCRIPT,
        txt_path,
        "-e", engine,
        "-l", language,
        "-f", FORMAT,
        "-o", output_base,
        "-d", output_dir,
    ]

    if engine == "xtts":
        # XTTS has a hard 400-token input limit; shorter target segments avoid
        # occasional overlong chunks from AlmondTTS's duration-based splitter.
        cmd.extend(["--max-duration", XTTS_MAX_DURATION])
    elif engine == "googletts":
        # Google Chirp HD handles long inputs well and produces better prosody
        # with more context. Target ~300-word segments (~120s at 2.5 wps) so
        # full sentences and multi-sentence spans are sent as single requests.
        cmd.extend(["--min-duration", "60", "--max-duration", "120"])

    return cmd


# ---------------------------------------------------------------------------
# Validation log writer
# ---------------------------------------------------------------------------

def append_job_log(txt_path, mp3_path, engine, language,
                   exit_code, started_at, finished_at, log_lines):
    """Append a human-readable entry to tts.log after each completed job."""

    # --- Input stats ---
    with open(txt_path, encoding="utf-8") as f:
        text = f.read()
    word_count = len(text.split())

    # --- Output stats ---
    mp3_exists  = os.path.exists(mp3_path)
    mp3_size_mb = round(os.path.getsize(mp3_path) / 1_048_576, 2) if mp3_exists else 0
    audio_dur_s = get_audio_duration(mp3_path) if mp3_exists else None

    # --- TTS parse ---
    tts = parse_almond_output(log_lines)

    # --- Derived metrics ---
    actual_wps = round(word_count / audio_dur_s, 2) if audio_dur_s else None
    elapsed_s  = round((finished_at - started_at).total_seconds(), 1)
    status     = "OK" if exit_code == 0 else "FAILED"

    def hms(s):
        if s is None: return "?"
        return f"{int(s//3600)}:{int(s%3600//60):02d}:{int(s%60):02d}"

    # --- Warnings: direct evidence of engine problems only ---
    warnings = []
    if tts["failed_count"]:
        ids = ", ".join(str(f["segment_id"]) for f in tts["failed_segments"])
        warnings.append(f"{tts['failed_count']} segment(s) failed (IDs: {ids})")
    if tts["duration_limit_hits"]:
        warnings.append(f"{tts['duration_limit_hits']} duration-limit hit(s)")
    if tts["outlier_count"]:
        parts = ", ".join(
            f"ID {o['segment_id']} ({o['duration_s']:.1f}s = {o['ratio']}× mean)"
            for o in tts["outlier_segments"]
        )
        warnings.append(f"{tts['outlier_count']} outlier segment(s): {parts}")

    lines = [
        f"{'='*70}",
        f"  chapter  : {os.path.basename(txt_path)}",
        f"  status   : {status}  (exit {exit_code})",
        f"  engine   : {engine}  language={language}",
        f"  started  : {started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"  elapsed  : {elapsed_s}s",
        f"",
        f"  input    : {word_count:,} words",
        f"  output   : {hms(audio_dur_s)}  ({mp3_size_mb} MB)",
        f"  segments : {tts['completed_segments']}/{tts['total_segments']} completed"
                      f"  {tts['failed_count']} failed"
                      f"  mean {tts['tts_audio_mean_s']}s",
        f"  wps      : {actual_wps} words/sec",
    ]
    if warnings:
        lines.append(f"")
        for w in warnings:
            lines.append(f"  *** {w}")

    entry = "\n".join(lines) + "\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

    # Also echo summary to terminal
    warn_str = "  *** " + " / ".join(warnings) if warnings else ""
    print(f"  [{status}] {hms(audio_dur_s)}  {mp3_size_mb} MB  "
          f"{tts['completed_segments']}/{tts['total_segments']} segs  "
          f"mean {tts['tts_audio_mean_s']}s/seg  "
          f"{actual_wps} wps{warn_str}")

    return tts


# ---------------------------------------------------------------------------
# Main chapter runner
# ---------------------------------------------------------------------------

def run_chapter(txt_path, engine, language):
    base    = os.path.splitext(os.path.basename(txt_path))[0]
    mp3_path = os.path.join(os.path.abspath(AUDIO_DIR), f"{base}.{FORMAT}")

    cmd = build_almond_command(
        txt_path,
        engine,
        language,
        base,
        os.path.abspath(AUDIO_DIR),
    )
    print(f"\n>>> {base}")
    print(" ".join(cmd))

    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    started_at = datetime.now(timezone.utc)
    log_lines  = []

    # Stream output to terminal AND capture for log parsing
    proc = subprocess.Popen(cmd, env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end="", flush=True)
        log_lines.append(line)
    proc.wait()

    finished_at = datetime.now(timezone.utc)

    tts = append_job_log(txt_path, mp3_path, engine, language,
                         proc.returncode, started_at, finished_at, log_lines)

    if proc.returncode != 0 or tts["failed_count"] > 0:
        if tts["failed_count"] > 0:
            print(f"ERROR: {base} had {tts['failed_count']} failed segment(s)")
        elif proc.returncode != 0:
            print(f"ERROR: {base} failed with exit code {proc.returncode}")
        return False
    return True


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run AlmondTTS on chapter files.")
    parser.add_argument(
        "-e", "--engine",
        default="xtts",
        choices=["xtts", "kokoro", "piper", "voxtral", "googletts"],
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
