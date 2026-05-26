#!/usr/bin/env python3
"""Split book.md into per-chapter plain text files for AlmondTTS.

Detects chapter boundaries where a <!-- Page --> comment is immediately
followed by a chapter marker line (INTRODUCTION, 1-9, CODA) and a title.

Output: output/chapters/ch00_introduction.txt, ch01_*.txt, …
"""

import re
import os

MD_PATH = "./output/book.md"
CHAPTERS_DIR = "./output/chapters"

# Matches the chapter-start pattern across three consecutive lines
BOUNDARY_RE = re.compile(
    r"<!-- Page \d+ -->\n([1-9]|INTRODUCTION|CODA)\n(.+)"
)


def slugify(text):
    text = text.lower()
    text = re.sub(r"[\"'""'']", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def clean(text):
    # Remove HTML page-marker comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Remove --- dividers
    text = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE)
    # Remove standalone numbers ≥ 10 (OCR'd book page numbers)
    text = re.sub(r"^\d{2,}\s*$", "", text, flags=re.MULTILINE)
    # Remove section break markers (* or * * * on their own line)
    text = re.sub(r"^[\*\s]+$", "", text, flags=re.MULTILINE)
    # Remove square brackets (editorial insertions like [They], [a Nazi newspaper])
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all chapter boundary positions
    boundaries = []
    for m in BOUNDARY_RE.finditer(content):
        marker = m.group(1)   # e.g. "1", "INTRODUCTION", "CODA"
        title  = m.group(2).strip()
        boundaries.append((m.start(), marker, title))

    if not boundaries:
        print("No chapter boundaries found.")
        return

    os.makedirs(CHAPTERS_DIR, exist_ok=True)

    for i, (start, marker, title) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(content)
        chunk = content[start:end]

        cleaned = clean(chunk)

        # Remove leading chapter number or keyword (e.g. "1\n", "INTRODUCTION\n")
        # so TTS doesn't read "one" / "INTRODUCTION" before the title
        cleaned = re.sub(r"^(INTRODUCTION|CODA|[1-9])\n", "", cleaned)

        # Build filename: ch00_introduction, ch01_title_slug, …
        if marker == "INTRODUCTION":
            prefix = "ch00"
        elif marker == "CODA":
            prefix = f"ch{len(boundaries) - 1:02d}"
        else:
            prefix = f"ch{int(marker):02d}"

        filename = f"{prefix}_{slugify(title)}.txt"
        path = os.path.join(CHAPTERS_DIR, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        word_count = len(cleaned.split())
        print(f"  {filename}  ({word_count:,} words)")

    print(f"\n{len(boundaries)} chapter(s) written to {CHAPTERS_DIR}/")


if __name__ == "__main__":
    main()
