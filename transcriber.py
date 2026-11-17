import importlib.util
import os

from engines import engine_from_config
from utils import TRANSCRIBER_CONFIG_DIR, read_json, write_private_json

# Saved under data/, which is git-ignored, and readable only by the current user.
# Holds the chosen engine and, if one was given, the OpenAI API key.
CONFIG_FILE = os.path.join(TRANSCRIBER_CONFIG_DIR, "transcriber.json")

OPENAI_MODEL = "whisper-1"
# English model; mlx-community/parakeet-tdt-0.6b-v3 adds 24 more European languages.
PARAKEET_MODEL = "mlx-community/parakeet-tdt-0.6b-v2"
# faster-whisper model name; "small.en" is ~3x smaller and faster but less accurate.
WHISPER_MODEL = "large-v3-turbo"

INSTALL_HINTS = {
    "parakeet": "pip install -r requirements-parakeet.txt",
    "whisper": "pip install -r requirements-whisper.txt",
}
ENGINE_MODULES = {
    "openai": "openai",
    "parakeet": "parakeet_mlx",
    "whisper": "faster_whisper",
}


def is_installed(engine):
    """Whether the engine's Python package is installed (without importing it)."""
    return importlib.util.find_spec(ENGINE_MODULES[engine]) is not None


def load_config():
    return read_json(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else {}


def save_config(engine, openai_key=None):
    """Save the engine choice, keeping any saved OpenAI key unless a new one is given."""
    config = load_config()
    config["engine"] = engine
    if openai_key:
        config["openai_key"] = openai_key
    write_private_json(CONFIG_FILE, config)


def load_saved_key():
    """Return the saved OpenAI API key, or None if there isn't one."""
    return load_config().get("openai_key") or None


class EngineNotInstalled(RuntimeError):
    pass


def import_failure(engine, error):
    """Explain why a local engine couldn't be imported.

    If the engine's package is missing, say how to install it. If it is
    installed but something it depends on failed to import, keep the real
    error: reinstalling the engine won't fix that.
    """
    if not is_installed(engine):
        return EngineNotInstalled(INSTALL_HINTS[engine])
    return RuntimeError(
        f"The {engine} engine is installed but failed to load: {error}. "
        "If a standard module such as _lzma is missing, your Python was built "
        "without it; create .venv with a different Python."
    )


class OpenAIBackend:
    def __init__(self, api_key):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def transcribe(self, path):
        with open(path, "rb") as audio_file:
            result = self.client.audio.transcriptions.create(
                model=OPENAI_MODEL, file=audio_file
            )
        return result.text.strip()


class ParakeetBackend:
    def __init__(self):
        try:
            from parakeet_mlx import from_pretrained
        except ImportError as error:
            raise import_failure("parakeet", error) from error
        print(f"Loading {PARAKEET_MODEL} (downloaded on first use, about 2.5 GB).")
        self.model = from_pretrained(PARAKEET_MODEL)

    def transcribe(self, path):
        return self.model.transcribe(path).text.strip()


class WhisperBackend:
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise import_failure("whisper", error) from error
        print(f"Loading Whisper {WHISPER_MODEL} (downloaded on first use, about 1.6 GB).")
        # "auto" uses an NVIDIA GPU if there is one, otherwise the CPU with int8.
        self.model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="auto")

    def transcribe(self, path):
        segments, _info = self.model.transcribe(path, beam_size=5)
        return " ".join(segment.text.strip() for segment in segments).strip()


class Transcriber:
    def __init__(self, engine=None, openai_key=None):
        config = load_config()
        self.engine = engine or engine_from_config(config)
        self.openai_key = openai_key or config.get("openai_key")
        self._backend = None

    @property
    def is_configured(self):
        if self.engine == "openai":
            return bool(self.openai_key)
        return self.engine is not None

    def _get_backend(self):
        # Created on first use: local models take a while to load.
        if self._backend is None:
            if self.engine == "openai":
                self._backend = OpenAIBackend(self.openai_key)
            elif self.engine == "parakeet":
                self._backend = ParakeetBackend()
            elif self.engine == "whisper":
                self._backend = WhisperBackend()
            else:
                raise RuntimeError("No transcription engine chosen. Run `python main.py login`.")
        return self._backend

    def transcribe(self, clip_file_path):
        return self._get_backend().transcribe(clip_file_path)
