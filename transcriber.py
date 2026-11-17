import os

from openai import OpenAI

from utils import TRANSCRIBER_CONFIG_DIR, read_json, write_private_json

# Saved under data/, which is git-ignored, and readable only by the current user.
KEY_FILE = os.path.join(TRANSCRIBER_CONFIG_DIR, "transcriber.json")


def load_saved_key():
    """Return the saved OpenAI API key, or None if there isn't one."""
    if not os.path.exists(KEY_FILE):
        return None
    return read_json(KEY_FILE).get("openai_key") or None


def save_key(key):
    write_private_json(KEY_FILE, {"openai_key": key})


class Transcriber:
    def __init__(self, openai_key=None):
        key = openai_key or load_saved_key()
        self.client = OpenAI(api_key=key) if key else None

    def transcribe(self, clip_file_path):
        with open(clip_file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        return transcription.text
