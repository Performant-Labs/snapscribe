#!/usr/bin/env python3
"""Translate chapter files from English to Mexican Spanish using Claude.

Reads output/chapters/ch*.txt, translates each via the Anthropic API,
and writes output/book-mx-es.md.

Usage:
    python translate_to_es.py                  # all chapters
    python translate_to_es.py ch01 ch02        # specific chapters
"""

import glob
import os
import re
import sys

import anthropic

CHAPTERS_DIR = "./output/chapters"
OUTPUT_FILE = "./output/book-mx-es.md"
CHUNK_WORDS = 4000

SYSTEM_PROMPT = (
    "You are a professional literary translator specializing in Mexican Spanish (es-MX). "
    "Translate the provided English text faithfully and naturally into Mexican Spanish. "
    "Preserve the author's voice, tone, and structure. Use Mexican Spanish vocabulary, "
    "idioms, and register — not Castilian or generic Latin American Spanish. "
    "Translate proper nouns only when a widely accepted Spanish equivalent exists. "
    "Output ONLY the translated text, with no commentary, no introductory phrases, "
    "and no labels."
)


def split_into_chunks(text: str, max_words: int = CHUNK_WORDS) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        w = len(para.split())
        if current_words + w > max_words and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_words = w
        else:
            current.append(para)
            current_words += w

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def translate_chunk(client: anthropic.Anthropic, chunk: str, chunk_num: int, total: int) -> str:
    print(f"    chunk {chunk_num}/{total} ({len(chunk.split())} words)…", end=" ", flush=True)
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": chunk}],
    ) as stream:
        result = stream.get_final_message()

    translation = result.content[0].text
    print("done")
    return translation


def translate_file(client: anthropic.Anthropic, path: str) -> str:
    with open(path, encoding="utf-8") as f:
        text = f.read()

    chunks = split_into_chunks(text)
    print(f"  {os.path.basename(path)} → {len(chunks)} chunk(s)")

    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        translated = translate_chunk(client, chunk, i, len(chunks))
        parts.append(translated)

    return "\n\n".join(parts)


def main():
    client = anthropic.Anthropic()

    all_chapters = sorted(glob.glob(os.path.join(CHAPTERS_DIR, "ch*.txt")))
    if not all_chapters:
        print(f"No chapter files found in {CHAPTERS_DIR}/")
        print("Run md_to_chapters.py first.")
        sys.exit(1)

    if len(sys.argv) > 1:
        filters = sys.argv[1:]
        all_chapters = [
            p for p in all_chapters
            if any(os.path.basename(p).startswith(f) for f in filters)
        ]
        if not all_chapters:
            print(f"No chapters matched: {sys.argv[1:]}")
            sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # Determine write mode: overwrite if all chapters, append if subset
    append_mode = len(sys.argv) > 1
    open_mode = "a" if append_mode else "w"

    print(f"Translating {len(all_chapters)} chapter(s) → {OUTPUT_FILE}\n")

    with open(OUTPUT_FILE, open_mode, encoding="utf-8") as out:
        for path in all_chapters:
            print(f"\n[{os.path.basename(path)}]")
            translation = translate_file(client, path)
            out.write(translation)
            out.write("\n\n")
            out.flush()

    print(f"\nDone. Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
