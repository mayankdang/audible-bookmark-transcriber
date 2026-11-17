# Audible bookmark transcriber

## Introduction

This is a small tool for [Audible](https://audible.com) users to easily extract their bookmarks from the audio books as text. You can transcribe with [OpenAI's Whisper API](https://openai.com/index/whisper) (paid), or for free on your own computer with [NVIDIA Parakeet](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) (Apple Silicon Macs) or [Whisper](https://github.com/SYSTRAN/faster-whisper).

> [!IMPORTANT]
> This tool is only meant to help users download and use the Audible books they **actually own**.

## Limitations
- It only supports English books for now (the local Whisper engine can handle other languages, but this is untested).
- Your Amazon account needs two-step verification (2FA) turned on to log in.
- It has only been tested on MacOS. Linux will probably work, but Windows is unlikely.

## User guide
Follow these steps to get started.

### Clone this repo.


### Install the necessary dependencies.
1. `ffmpeg` (if you need to install `brew`, follow the instructions [here](https://brew.sh/))
```
brew install ffmpeg
```  
2. `jq`
```
brew install jq
```  
3. The Python dependencies. A virtual environment keeps them separate from the rest of your system:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
4. Optional: a free, local transcription engine, if you don't want to use the paid OpenAI API. Install the one you'll use:

| Engine | Install | Runs on | Model download | Time per 30-second clip* |
| --- | --- | --- | --- | --- |
| NVIDIA Parakeet (recommended free option) | `pip install -r requirements-parakeet.txt` | Apple Silicon Macs, using the GPU | about 2.5 GB | under 1 second |
| Whisper (large-v3-turbo) | `pip install -r requirements-whisper.txt` | Any computer; on a Mac it uses the CPU | about 1.6 GB | about 10 seconds |

\*Measured on an M1 Pro. On test clips, both matched the OpenAI API's transcription almost word for word; the differences were mostly character names.

With a local engine, your audio never leaves your computer. The model downloads from Hugging Face the first time you transcribe and is then reused from Hugging Face's shared cache (`~/.cache/huggingface/hub`), so other projects can use it too. To free the space later:
```
hf cache rm model/mlx-community/parakeet-tdt-0.6b-v2
hf cache rm model/mobiuslabsgmbh/faster-whisper-large-v3-turbo
```
To keep models somewhere else, set the `HF_HOME` environment variable to another folder.

> [!NOTE]
> Parakeet needs Python's built-in `lzma` module. If you install Python with pyenv, run `brew install xz` *before* `pyenv install`, or Python is built without it. Check with `python -c "import lzma"`.

Run the commands below with the virtual environment active.

### Log in to your Audible account and choose a transcription engine

> [!IMPORTANT]
> **Turn on two-step verification (2FA) on your Amazon account before logging in.** Without it, Amazon blocks the login. You can turn it on under Your Account → Login & Security → 2-Step Verification; an authenticator app works best.

> [!NOTE]
> **Login now happens in your browser.** Earlier versions asked for your Amazon password in the terminal. That flow broke on Amazon's verification-code (CVF) step, so it has been replaced: the tool never sees your Amazon password.

Run:
```
python main.py login
```
The command asks for:
- Your Amazon/Audible email. This is only used to label the saved login.
- The country/region of your Audible account.

It then prints a login URL:
1. Open the URL in your browser and sign in to Amazon. Enter your 2FA code when Amazon asks for it.
2. After you sign in, the browser shows a "Page not found" error. That's expected.
3. Copy the full URL from the browser's address bar and paste it into the terminal.

Finally it asks how to transcribe your clips:
1. **OpenAI Whisper API**: paid per minute of audio. It asks for your OpenAI API key (typing is hidden); if a key is already saved, it asks whether to reuse it or enter a new one. If you don't have a key, follow [the steps here](https://platform.openai.com/docs/quickstart).
2. **NVIDIA Parakeet**: free, runs on your Mac. Only offered on Apple Silicon Macs, where it's the default.
3. **Whisper**: free, runs on your computer.

Press Enter to keep the default.

You can run `python main.py login` again at any time to switch engines or change the saved OpenAI key; it won't ask you to sign in to Amazon again. To switch Amazon accounts, delete `data/audible_configs` first.

Your Amazon login tokens and OpenAI key are saved under `data/`, which is excluded from git and readable only by your user account. Never commit or share that folder.

### Get a list of your Audible books
Run:
```
python main.py list
```
If everything works as expected, you should see a list of Audible books (ASIN + title) printed.

### Extract bookmarks and transcribe
Run:
```
python main.py transcribe_bookmarks <ASIN>
```
where `<ASIN>` is the book ID you want to use.

### Wait for the code to run
It will take a while. Basically the code performs the following steps:
1. Download the original audio book file, remove the DRM using your Audible user credential, and save it as a `.mp4` file.
> [!IMPORTANT]
> Anti-Piracy Notice
> 
> Please only use these tools for gaining full access to your own ebooks for archiving/conversion/convenience. De-drmed ebooks should not be uploaded to open servers, torrents, or other methods of mass distribution. No help will be given to people doing such things. Authors, retailers and publishers all need to make a living, so that they can continue to produce books for us to read. Don’t be a parasite.
> 
> The converted `.mp4` file is only meant for your personal use. DO NOT distribute! After the code finish running, you should delete this file to avoid leaks.

2. Extract the bookmarks you created for this book, specifically, the start and end time of each clip.
3. Extract each clip as separate audio files.
4. Transcribe the audio clips with the engine you chose.

### Completed.
The transcribed notes will be saved in this file: `data/audio/<ASIN>/transcribed_notes.json`.

Each note is keyed by where its clip starts in the book, in milliseconds, and the notes are listed in the order they occur in the book.

Only clips are transcribed. Plain bookmarks (a single point in time, with no start and end) have no audio range, so they are skipped.

## Development
Run the unit tests (no extra packages needed):
```
python -m unittest discover -s tests
```
