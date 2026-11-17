import unittest

from utils import format_time, is_yes, mask_key


class MaskKeyTest(unittest.TestCase):
    def test_shows_only_prefix_and_last_four(self):
        self.assertEqual(mask_key("sk-proj-abcdefghijklmnop1234"), "sk-…1234")

    def test_short_values_are_fully_hidden(self):
        self.assertEqual(mask_key("sk-12345"), "…")
        self.assertEqual(mask_key(""), "…")


class IsYesTest(unittest.TestCase):
    def test_empty_answer_uses_default(self):
        self.assertTrue(is_yes("", default=True))
        self.assertFalse(is_yes("  ", default=False))

    def test_explicit_answers(self):
        for answer in ("y", "Y", "yes", " YES "):
            self.assertTrue(is_yes(answer, default=False))
        for answer in ("n", "no", "N", "nope"):
            self.assertFalse(is_yes(answer, default=True))


class FormatTimeTest(unittest.TestCase):
    def test_formats_hours_minutes_seconds_millis(self):
        self.assertEqual(format_time(3_723_045), "01:02:03.045")
        self.assertEqual(format_time(0), "00:00:00.000")


if __name__ == "__main__":
    unittest.main()
