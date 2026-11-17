import os
import platform
import sys
from getpass import getpass

from audible_manager import AudibleManager
from engines import (
    ENGINES,
    available_engines,
    default_engine,
    engine_from_config,
    parse_engine_choice,
)
from transcriber import (
    INSTALL_HINTS,
    Transcriber,
    is_installed,
    load_config,
    load_saved_key,
    save_config,
)
from utils import is_yes, mask_key, secure_data_dir

COUNTRY_CODES = {
    "us": "US and all other countries not listed",
    "ca": "Canada",
    "uk": "UK and Ireland",
    "au": "Australia and New Zealand",
    "fr": "France, Belgium, Switzerland",
    "de": "Germany, Austria, Switzerland",
    "jp": "Japan",
    "it": "Italy",
    "in": "India",
    "es": "Spain",
    "br": "Brazil",
}


def has_valid_configs(transcriber, manager):
    return transcriber.is_configured and manager.auth is not None


def check_for_valid_configs():
    transcriber = Transcriber()
    manager = AudibleManager(transcriber=transcriber)
    if not has_valid_configs(transcriber=transcriber, manager=manager):
        print(
            "Please run `python main.py login` to authenticate to Audible and OpenAI."
        )
        return None, None
    return transcriber, manager


def ask_country_code():
    print(
        "Please enter the two-letter Audible account country code from the following options:"
    )
    for code, description in COUNTRY_CODES.items():
        print(f"- {code}: {description}")

    country_code = input("Enter your country code: ").strip().lower()
    while country_code not in COUNTRY_CODES:
        print(
            "Invalid country code. Please enter a valid two-letter country code from the list above."
        )
        country_code = input("Enter your country code: ").strip().lower()
    return country_code


def ask_engine():
    """Ask which transcription engine to use; Enter keeps the saved or free default."""
    options = available_engines(platform.system(), platform.machine())
    default = default_engine(engine_from_config(load_config()), options)

    print("How should your clips be transcribed?")
    for number, engine in enumerate(options, start=1):
        marker = "  (default)" if engine == default else ""
        print(f"  {number}. {ENGINES[engine]}{marker}")

    while True:
        answer = input("Enter a number, or press Enter for the default: ")
        choice = parse_engine_choice(answer, options, default)
        if choice:
            return choice
        print("Please enter one of the numbers above.")


def ask_openai_key():
    """Return the saved OpenAI key if the user wants it, otherwise a new one."""
    saved_key = load_saved_key()
    if saved_key:
        answer = input(
            f"Found a saved OpenAI API key ({mask_key(saved_key)}). Use it? [Y/n]: "
        )
        if is_yes(answer, default=True):
            return saved_key

    key = ""
    while not key:
        key = getpass("Enter your OpenAI API key (input is hidden): ").strip()
    return key


def print_install_hint(engine):
    print(f"The {engine} engine isn't installed yet. Install it with:")
    print(f"  {INSTALL_HINTS[engine]}")


def login():
    manager = AudibleManager(transcriber=None)

    if manager.auth is not None:
        print(
            f"Already logged in to Audible as {manager.username or 'a saved account'}. "
            "To switch accounts, delete data/audible_configs and run login again."
        )
    else:
        username = input(
            "Enter your Amazon/Audible email (only used to label this login): "
        ).strip()
        country_code = ask_country_code()
        if not manager.authenticate(username=username, country_code=country_code):
            return

    engine = ask_engine()
    openai_key = ask_openai_key() if engine == "openai" else None
    save_config(engine, openai_key)
    print(f"Transcription engine: {ENGINES[engine]}.")
    if not is_installed(engine):
        print_install_hint(engine)

    manager.transcriber = Transcriber(engine=engine, openai_key=openai_key)
    manager.save_library()
    print("Login complete. Run `python main.py list` to see your books.")


def transcribe_bookmarks(asin):
    transcriber, manager = check_for_valid_configs()
    if not (transcriber and manager):
        return
    book = manager.get_book_by_asin(asin)
    if book is None:
        print("Book not found in library. Run `python main.py list` to refresh it.")
        return
    # Check before the long download, not after it.
    if not is_installed(transcriber.engine):
        print_install_hint(transcriber.engine)
        return

    print(f"Downloading book {book['title']}. This may take a few minutes.")
    if manager.download_and_convert_book(asin) != 0:
        print("Downloading or converting the book failed. See the output above.")
        return

    print(f"Extracting bookmarked clips from {book['title']}.")
    manager.extract_audio_clips(asin)

    print(f"Transcribing bookmarked clips from {book['title']}.")
    manager.transcribe_audio_clips(asin)


def main():
    # Everything this tool writes (tokens, keys, decrypted audio) is private
    # to the current user.
    os.umask(0o077)
    secure_data_dir()

    if len(sys.argv) <= 1:
        print("No command provided. Use one of: login, list, transcribe_bookmarks <ASIN>")
        return

    command = sys.argv[1]
    if command == "login":
        login()
    elif command == "list":
        transcriber, manager = check_for_valid_configs()
        if transcriber and manager:
            manager.save_library()
            library = manager.load_library()
            print("ASIN\t\t Title")
            for book in library:
                print(f"{book['asin']}\t {book['title']}")
    elif command == "transcribe_bookmarks":
        if len(sys.argv) < 3:
            print(
                "Please provide the ASIN of the book you want to transcribe.\n Usage: python main.py transcribe_bookmarks <ASIN>\n To get a list of ASINs, run `python main.py list`"
            )
            return
        transcribe_bookmarks(sys.argv[2])
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
