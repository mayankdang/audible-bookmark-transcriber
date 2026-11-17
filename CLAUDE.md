# CLAUDE.md

Guidance for Claude Code (and other contributors) working in this repository.

## What this project does

A small Python CLI that turns the clips you bookmark in Audible audiobooks into text:

1. Logs in to Audible through the user's browser and saves the session tokens locally.
2. Downloads a book the user owns, removes the DRM with the user's own credentials, and saves it as an `.mp4`.
3. Reads the book's annotations and cuts each clip out as an `.mp3` with `ffmpeg`.
4. Sends each clip to OpenAI's Whisper API and saves the transcriptions, in book order, to `data/audio/<ASIN>/transcribed_notes.json`.

It is only for books the user actually owns. Never add features meant for sharing or distributing DRM-free audio.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # pinned versions
python main.py login                       # browser login + OpenAI key
python main.py list                        # refresh and print the library
python main.py transcribe_bookmarks <ASIN>
python -m unittest discover -s tests       # unit tests, no extra packages
```

System tools: `ffmpeg` and `jq` (Homebrew on macOS).

## Layout

| File | Role |
| --- | --- |
| `main.py` | CLI entry point and prompts (login, list, transcribe_bookmarks). |
| `audible_manager.py` | Audible login, library, download, clip extraction and transcription loop. |
| `audible-convert.sh` | Downloads a book with `audible-cli` and decrypts/re-encodes it with `ffmpeg`. |
| `transcriber.py` | OpenAI client and loading/saving the user's API key. |
| `notes.py` | Pure helpers: pick clips from annotations, compute clip windows, sort notes. |
| `utils.py` | Paths, time formatting, JSON and private-file helpers, subprocess environment. |
| `tests/` | `unittest` tests for the pure helpers. |
| `data/` | All runtime state. Git-ignored; never commit anything from it. |

## Conventions

- Keep business logic in pure functions (see `notes.py`); do file, network and subprocess work at the edges.
- Write or update tests before changing core logic, and run the test suite before committing.
- Build paths from the constants in `utils.py` (`PROJECT_DIR`, `DATA_DIR`, ...), never from `os.getcwd()`.
- Run external programs with an argument list (`subprocess.run([...])`), never `shell=True`.
- Pin new dependencies to exact versions in `requirements.txt`.
- Transcribed notes are a JSON object keyed by clip start position in milliseconds (as a string). Always write it through `sort_notes` so it stays in book order, and keep the format backward compatible with existing files.

## Security rules

This tool handles Amazon session tokens, a device private key, an OpenAI API key and DRM-free audio. Treat all of them as secrets.

- Everything sensitive lives under `data/`, which is git-ignored. Don't move secrets elsewhere or loosen that ignore rule.
- Write credential files with `write_private_json` / `make_private` (mode `0600`); `main.py` also sets `umask 077` and locks `data/` to the current user.
- Never print, log or echo tokens, API keys, Audible activation bytes or voucher keys. In `audible-convert.sh`, `$decrypt` contains a decryption key and must never be printed.
- Never ask for or store the user's Amazon password. Login goes through the browser (`Authenticator.from_login_external`); the Amazon account needs 2FA turned on.
- Don't commit real annotation files, transcripts, audio, library exports or logs, even as test fixtures. Use small made-up data in tests.
- Don't add network calls other than to Amazon/Audible (via the `audible` libraries) and OpenAI.

## Git

- `origin` is this fork; `upstream` is the original, unmaintained project.
- Work on a branch and keep commits focused.
