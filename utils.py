import json
import math
import os
import sys

# Resolve paths from this file, not the current directory, so the tool works
# no matter where it is run from.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
AUDIBLE_CONFIG_DIR = os.path.join(DATA_DIR, "audible_configs")
TRANSCRIBER_CONFIG_DIR = os.path.join(DATA_DIR, "transcriber_configs")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")


def format_time(milliseconds):
    hours = math.floor(milliseconds / (1000 * 60 * 60))
    minutes = math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60))
    seconds = math.floor(((milliseconds % (1000 * 60 * 60)) % (1000 * 60)) / 1000)
    millis = milliseconds % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


def mask_key(key):
    """Return a key with everything but its prefix and last four characters hidden."""
    if not key or len(key) < 12:
        return "…"
    return f"{key[:3]}…{key[-4:]}"


def is_yes(answer, default):
    """Interpret a yes/no answer typed at a prompt."""
    answer = answer.strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def make_private(path):
    """Restrict a file to the current user (owner read/write only)."""
    if os.path.exists(path):
        os.chmod(path, 0o600)


def write_private_json(path, data):
    """Write JSON that holds credentials, readable only by the current user."""
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    make_private(path)


def secure_data_dir():
    """Lock down data/ so other users on this machine can't read tokens, keys or audio.

    Also tightens files created by older versions of this tool, which were
    readable by everyone.
    """
    if not os.path.isdir(DATA_DIR):
        return
    os.chmod(DATA_DIR, 0o700)
    for config_dir in (AUDIBLE_CONFIG_DIR, TRANSCRIBER_CONFIG_DIR):
        if os.path.isdir(config_dir):
            os.chmod(config_dir, 0o700)
            for name in os.listdir(config_dir):
                make_private(os.path.join(config_dir, name))


def subprocess_env():
    """Environment for helper processes, with this Python's bin dir on PATH.

    audible-convert.sh calls the `audible` command from audible-cli, which is
    installed next to this interpreter (for example in .venv/bin). Putting that
    directory first means the virtual environment doesn't need activating.
    """
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")
    env["AUDIBLE_CONFIG_DIR"] = AUDIBLE_CONFIG_DIR
    return env
