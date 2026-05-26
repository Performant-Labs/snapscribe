# Snapscribe

> Capture browser pages with a keyboard shortcut, then OCR them into an EPUB using Apple Vision — no cloud, no GPU, no fuss.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](#requirements)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#requirements)

---

## How it works

1. **Chrome extension** — press `Cmd+Shift+U` on any browser page to save a numbered PNG screenshot to your Downloads folder.
2. **`snapscribe.py`** — reads the PNGs, runs OCR via Apple's Vision framework, and produces a Markdown file and an EPUB.

Typical workflow: open a book or document in the browser, page through it pressing the shortcut each time, then run the script once to get a clean EPUB.

---

## Requirements

- **macOS** (Apple Vision OCR is macOS-only)
- Python 3.9+
- Google Chrome (or any Chromium browser)
- [pandoc](https://pandoc.org/installing.html) — required by `pypandoc` to write EPUB files

Install pandoc with Homebrew:

```bash
brew install pandoc
```

---

## Installation

### 1 — Python dependencies

```bash
git clone https://github.com/Performant-Labs/snapscribe.git
cd snapscribe
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2 — Chrome extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked** and select the `snapscribe` folder
4. The extension is now active — no restart needed

The default shortcut is `Cmd+Shift+U`. To change it, go to `chrome://extensions/shortcuts`.

---

## Usage

### Step 1 — Capture pages

Open the document in your browser. Press **`Cmd+Shift+U`** once per page. Each press saves a file named `snap_0001.png`, `snap_0002.png`, … to your Downloads folder and flashes the screen briefly as confirmation.

When done, move (or copy) all the PNGs into the `captures/` directory:

```bash
mv ~/Downloads/snap_*.png captures/
```

### Step 2 — Run OCR and build EPUB

```bash
# All images in captures/
python snapscribe.py

# Single page only
python snapscribe.py --page 42

# Page range
python snapscribe.py --start 10 --end 25

# Append a range to an existing output file
python snapscribe.py --start 26 --end 50 --append
```

Output lands in `output/`:

| File | Contents |
|---|---|
| `output/book.md` | Raw OCR text as Markdown |
| `output/book.epub` | Final EPUB ready to open in any reader |

---

## Project structure

```
snapscribe/
├── background.js       # Chrome extension service worker
├── manifest.json       # Extension manifest (v3)
├── snapscribe.py       # OCR → EPUB pipeline
├── requirements.txt    # Python dependencies
├── captures/           # Drop your PNGs here (git-ignored)
└── output/             # Generated Markdown and EPUB (git-ignored)
```

---

## Tips

- **Zoom to fit** the full page before capturing for best OCR accuracy.
- Run in **append mode** (`--append`) to process a book in batches without losing earlier work.
- The `captures/` counter resets each time Chrome restarts. Rename files before mixing sessions to avoid collisions.
- OCR quality is entirely driven by Apple Vision — no configuration needed.

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE) © [Performant Labs](https://github.com/Performant-Labs)
