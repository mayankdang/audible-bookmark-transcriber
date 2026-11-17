import unittest

from notes import clip_records, clip_window, sort_notes


def clip(start, end, **extra):
    return {"type": "audible.clip", "startPosition": start, "endPosition": end, **extra}


class SortNotesTest(unittest.TestCase):
    def test_orders_by_numeric_timestamp_not_text(self):
        # As text, "9000" sorts after "10000"; in the book it comes first.
        notes = {"10000": "second", "9000": "first", "250000": "third"}
        self.assertEqual(list(sort_notes(notes)), ["9000", "10000", "250000"])

    def test_keeps_every_transcription(self):
        notes = {"3": "c", "1": "a", "2": "b"}
        self.assertEqual(sort_notes(notes), {"1": "a", "2": "b", "3": "c"})

    def test_does_not_modify_input(self):
        notes = {"2": "b", "1": "a"}
        sort_notes(notes)
        self.assertEqual(list(notes), ["2", "1"])

    def test_empty(self):
        self.assertEqual(sort_notes({}), {})


class ClipRecordsTest(unittest.TestCase):
    def test_keeps_only_clips_in_book_order(self):
        records = [
            clip("50000", "80000"),
            {"type": "audible.bookmark", "startPosition": "1000"},
            clip("9000", "39000"),
            {"type": "audible.last_heard", "startPosition": "5"},
            clip("10000", "40000"),
        ]
        starts = [r["startPosition"] for r in clip_records(records)]
        self.assertEqual(starts, ["9000", "10000", "50000"])


class ClipWindowTest(unittest.TestCase):
    def test_start_and_duration_with_millisecond_precision(self):
        self.assertEqual(clip_window(clip("1000", "31500")), (1000, 30.5))

    def test_rejects_empty_or_reversed_clips(self):
        self.assertIsNone(clip_window(clip("5000", "5000")))
        self.assertIsNone(clip_window(clip("5000", "4000")))

    def test_rejects_clips_missing_positions(self):
        self.assertIsNone(clip_window({"type": "audible.clip", "startPosition": "1"}))
        self.assertIsNone(clip_window({"type": "audible.clip", "endPosition": "1"}))


if __name__ == "__main__":
    unittest.main()
