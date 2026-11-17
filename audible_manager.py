import os
import readline  # noqa: F401 - lets macOS terminals accept the long login URL paste
import subprocess

import audible
import toml

from notes import clip_records, clip_window, sort_notes
from utils import (
    AUDIBLE_CONFIG_DIR,
    AUDIO_DIR,
    PROJECT_DIR,
    format_time,
    make_private,
    read_json,
    subprocess_env,
    write_json,
    write_private_json,
)

AUTH_FILE = os.path.join(AUDIBLE_CONFIG_DIR, "audible.json")
USERNAME_FILE = os.path.join(AUDIBLE_CONFIG_DIR, "username.json")
LIBRARY_FILE = os.path.join(AUDIBLE_CONFIG_DIR, "library.json")
CONVERT_SCRIPT = os.path.join(PROJECT_DIR, "audible-convert.sh")


class AudibleManager:
    def __init__(self, transcriber):
        # Load saved Audible credentials if there are any; otherwise auth stays None.
        self.transcriber = transcriber
        os.environ["AUDIBLE_CONFIG_DIR"] = AUDIBLE_CONFIG_DIR
        self.auth = None
        self.username = None

        if os.path.exists(AUTH_FILE):
            self.auth = audible.Authenticator.from_file(AUTH_FILE)
            if os.path.exists(USERNAME_FILE):
                self.username = read_json(USERNAME_FILE).get("username")

    def _generate_toml_config(self, title, primary_profile, country_code):
        """
        Generate the config file audible-cli reads (used by audible-convert.sh).
        """
        config = {
            "title": title,
            "APP": {"primary_profile": primary_profile},
            "profile": {
                primary_profile: {
                    "auth_file": "audible.json",
                    "country_code": country_code,
                }
            },
        }
        with open(os.path.join(AUDIBLE_CONFIG_DIR, "config.toml"), "w") as file:
            toml.dump(config, file)

    def _book_dir(self, asin):
        return os.path.join(AUDIO_DIR, asin)

    def _find_annotation_file(self, book_dir):
        """
        Find the annotation file for the book (which contains the clips bookmarked by the user) in the given directory.
        """
        for filename in os.listdir(book_dir):
            if filename.endswith("-annotations.json"):
                return os.path.join(book_dir, filename)
        return None

    def _extract_clips_metadata(self, asin):
        """
        Return the book's clip annotations, in the order they occur in the book.
        """
        annotation_file_path = self._find_annotation_file(self._book_dir(asin))
        if not annotation_file_path:
            print(f"Annotation file not found for {asin}.")
            return []
        return clip_records(read_json(annotation_file_path)["payload"]["records"])

    def authenticate(self, username, country_code):
        """
        Log in to Audible through the browser and save the credentials.

        Returns True on success.
        """
        print("Creating new credentials and config files.")
        try:
            # Log in through a real browser so Amazon's own pages handle
            # verification codes (CVF), 2FA and captchas.
            self.auth = audible.Authenticator.from_login_external(
                locale=country_code, with_username=False
            )
        except Exception as error:  # the library raises several error types
            self.auth = None
            print(f"Login failed ({type(error).__name__}). Please try again.")
            return False

        os.makedirs(AUDIBLE_CONFIG_DIR, mode=0o700, exist_ok=True)
        self.auth.to_file(AUTH_FILE)
        make_private(AUTH_FILE)
        write_private_json(USERNAME_FILE, {"username": username})
        self._generate_toml_config("Audible Config File", "audible", country_code)
        self.username = username
        print("Signed in successfully.")
        return True

    def save_library(self):
        """
        Save the user's Audible library to a JSON file.
        """
        with audible.Client(auth=self.auth) as client:
            library = client.get(
                "1.0/library",
                num_results=1000,
                response_groups="product_desc, product_attrs, customer_rights",
                sort_by="-PurchaseDate",
            )
        write_json(LIBRARY_FILE, library["items"])

    def load_library(self):
        return read_json(LIBRARY_FILE)

    def get_book_by_asin(self, asin):
        """
        Get the book details from the library using the ASIN.
        """
        for book in self.load_library():
            if book["asin"] == asin:
                return book
        return None

    def download_and_convert_book(self, asin):
        """
        Download the book with the given ASIN and convert it to an MP4 file.

        The conversion is done by audible-convert.sh, which loads the user's
        credentials from the config file to remove the DRM. Returns the
        script's exit code (0 on success).
        """
        with subprocess.Popen(
            [CONVERT_SCRIPT, asin, f"{asin}.mp4"],
            text=True,
            stdout=subprocess.PIPE,
            # Merge stderr into stdout: reading only stdout while a long
            # download fills the stderr pipe would hang both processes.
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            env=subprocess_env(),
        ) as proc:
            for line in proc.stdout:
                print(line.rstrip())
        return proc.returncode

    def extract_audio_clips(self, asin):
        """
        Extract audio clips from the book and save them as individual audio files.
        """
        book_dir = self._book_dir(asin)
        audio_clips_dir = os.path.join(book_dir, "clips")
        os.makedirs(audio_clips_dir, exist_ok=True)
        for clip in self._extract_clips_metadata(asin):
            window = clip_window(clip)
            if window is None:
                print(f"Skipping clip at {clip.get('startPosition')}: it has no audio range.")
                continue
            start_ms, duration_seconds = window
            clip_path = os.path.join(audio_clips_dir, f"clip_{clip['startPosition']}.mp3")
            if os.path.exists(clip_path):
                continue  # cut on an earlier run
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-y",
                    "-loglevel",
                    "error",
                    # Seeking before -i jumps straight to the clip instead of
                    # decoding the book from the beginning for every clip.
                    "-ss",
                    format_time(start_ms),
                    "-i",
                    os.path.join(book_dir, f"{asin}.mp4"),
                    "-t",
                    f"{duration_seconds:.3f}",
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    "-acodec",
                    "libmp3lame",
                    clip_path,
                ],
                capture_output=True,
                text=True,
                cwd=PROJECT_DIR,
            )
            if result.returncode != 0:
                print(f"ffmpeg failed for clip at {format_time(start_ms)}:")
                print(result.stderr.strip())
                # Don't leave a partial file that later runs would treat as done.
                if os.path.exists(clip_path):
                    os.remove(clip_path)

    def _save_notes(self, path, notes):
        write_json(path, sort_notes(notes))

    def transcribe_audio_clips(self, asin):
        book_dir = self._book_dir(asin)
        audio_clips_dir = os.path.join(book_dir, "clips")
        transcribed_notes_file = os.path.join(book_dir, "transcribed_notes.json")

        transcribed_notes = (
            read_json(transcribed_notes_file)
            if os.path.exists(transcribed_notes_file)
            else {}
        )

        for clip in self._extract_clips_metadata(asin):
            start_position = clip["startPosition"]
            if start_position in transcribed_notes:
                print(f"Transcription for {start_position} already exists.")
                continue
            clip_file_path = os.path.join(audio_clips_dir, f"clip_{start_position}.mp3")
            if not os.path.exists(clip_file_path):
                print(f"Skipping {clip_file_path}: the clip wasn't extracted.")
                continue
            print(f"Transcribing {clip_file_path}.")
            transcribed_notes[start_position] = self.transcriber.transcribe(
                clip_file_path
            )
            # Save after every clip so an API error doesn't lose earlier work.
            self._save_notes(transcribed_notes_file, transcribed_notes)

        # Always rewrite the file so notes from older runs end up in book order too.
        self._save_notes(transcribed_notes_file, transcribed_notes)
        print(f"Succeeded. Transcriptions saved to {transcribed_notes_file}.")
