# Contributing to Snapscribe

Thanks for your interest in contributing!

## Ways to contribute

- **Bug reports** — open an issue describing what happened, what you expected, and your macOS + Chrome versions.
- **Feature requests** — open an issue with a clear use case before writing code.
- **Pull requests** — fixes and improvements are welcome; open an issue first for anything non-trivial so we can align on approach.

## Development setup

```bash
git clone https://github.com/Performant-Labs/snapscribe.git
cd snapscribe
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Load the extension in Chrome from `chrome://extensions/` with **Developer mode** enabled (see the README for details).

## Pull request guidelines

- Keep changes focused — one concern per PR.
- Update the README if you change user-facing behaviour.
- Python code should pass `python -m py_compile snapscribe.py` without errors.
- Describe *what* and *why* in the PR description; the diff covers the *how*.

## Code of conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Please be kind and constructive.
