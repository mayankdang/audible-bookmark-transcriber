"""Pure helpers for turning Audible annotations into ordered notes.

Nothing here touches the filesystem, the network or a subprocess.
"""

CLIP_TYPE = "audible.clip"


def clip_records(records):
    """Return the clip annotations, in the order they occur in the book.

    Audible's annotation file lists records in no useful order and also
    contains point bookmarks and the last-heard position, which have no
    audio range to transcribe.
    """
    clips = [r for r in records if r.get("type") == CLIP_TYPE]
    return sorted(clips, key=lambda r: int(r.get("startPosition", 0)))


def clip_window(record):
    """Return (start_ms, duration_seconds) for a clip, or None if unusable."""
    try:
        start = int(record["startPosition"])
        end = int(record["endPosition"])
    except (KeyError, TypeError, ValueError):
        return None
    if end <= start:
        return None
    return start, (end - start) / 1000


def sort_notes(notes):
    """Return transcribed notes ordered by their start position in the book.

    Keys are start positions in milliseconds, stored as strings, so they
    must be compared as numbers ("9000" comes before "10000").
    """
    return dict(sorted(notes.items(), key=lambda item: int(item[0])))
