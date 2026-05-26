#!/usr/bin/env python3
"""
OCR browser screenshots into an EPUB using Apple Vision.

Usage examples:
    python snapscribe.py
    python snapscribe.py --page 42
    python snapscribe.py --start 10 --end 25
    python snapscribe.py --start 50 --end 60 --append
"""

import os
import argparse
from ocrmac.ocrmac import OCR
import pypandoc

CAPTURES_DIR = "./captures"
OUTPUT_DIR = "./output"
JOB_NAME = "book"
MD_PATH = os.path.join(OUTPUT_DIR, f"{JOB_NAME}.md")
EPUB_PATH = os.path.join(OUTPUT_DIR, f"{JOB_NAME}.epub")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, help="Process only a single page number (e.g. 42)")
    parser.add_argument("--start", type=int, help="Start of page range (inclusive)")
    parser.add_argument("--end", type=int, help="End of page range (inclusive)")
    parser.add_argument("--append", action="store_true", help="Append to existing markdown instead of overwriting")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.page is not None:
        filename = f"snap_{args.page:04d}.png"
        png_files = [filename] if os.path.exists(os.path.join(CAPTURES_DIR, filename)) else []

    elif args.start is not None and args.end is not None:
        png_files = []
        for num in range(args.start, args.end + 1):
            filename = f"snap_{num:04d}.png"
            if os.path.exists(os.path.join(CAPTURES_DIR, filename)):
                png_files.append(filename)
        png_files.sort()

    else:
        png_files = sorted(
            [f for f in os.listdir(CAPTURES_DIR) if f.lower().endswith(".png")]
        )

    if not png_files:
        print("No matching PNG files found.")
        return

    print(f"Found {len(png_files)} image(s) to process.")

    all_text = []

    for filename in png_files:
        print(f"Processing {filename}...")
        image_path = os.path.join(CAPTURES_DIR, filename)
        page_lines = [text for text, _conf, _bbox in OCR(image_path).recognize()]

        page_text = "\n".join(page_lines)
        page_num = filename.replace("snap_", "").replace(".png", "")
        all_text.append(f"<!-- Page {page_num} -->\n{page_text}")

    new_content = "\n\n---\n\n".join(all_text)

    if args.append and os.path.exists(MD_PATH):
        with open(MD_PATH, "a") as f:
            f.write("\n\n---\n\n" + new_content)
        print(f"Appended to existing Markdown: {MD_PATH}")
    else:
        with open(MD_PATH, "w") as f:
            f.write(new_content)
        print(f"Markdown saved: {MD_PATH}")

    print("Creating EPUB...")
    pypandoc.convert_file(MD_PATH, "epub", outputfile=EPUB_PATH)
    print(f"EPUB created: {EPUB_PATH}")

    print("\nDone!")

if __name__ == "__main__":
    main()
