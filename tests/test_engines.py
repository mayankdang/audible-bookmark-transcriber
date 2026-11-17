import unittest

from engines import (
    available_engines,
    default_engine,
    engine_from_config,
    parse_engine_choice,
)


class AvailableEnginesTest(unittest.TestCase):
    def test_apple_silicon_gets_parakeet(self):
        self.assertEqual(
            available_engines("Darwin", "arm64"), ["openai", "parakeet", "whisper"]
        )

    def test_other_machines_skip_parakeet(self):
        self.assertEqual(available_engines("Darwin", "x86_64"), ["openai", "whisper"])
        self.assertEqual(available_engines("Linux", "x86_64"), ["openai", "whisper"])
        self.assertEqual(available_engines("Linux", "aarch64"), ["openai", "whisper"])


class EngineFromConfigTest(unittest.TestCase):
    def test_reads_saved_engine(self):
        self.assertEqual(engine_from_config({"engine": "parakeet"}), "parakeet")

    def test_older_config_with_only_a_key_means_openai(self):
        self.assertEqual(engine_from_config({"openai_key": "sk-abc"}), "openai")

    def test_nothing_saved(self):
        self.assertIsNone(engine_from_config({}))
        self.assertIsNone(engine_from_config({"openai_key": ""}))

    def test_unknown_engine_is_ignored(self):
        self.assertIsNone(engine_from_config({"engine": "google"}))


class DefaultEngineTest(unittest.TestCase):
    def test_keeps_the_saved_choice(self):
        self.assertEqual(default_engine("whisper", ["openai", "parakeet", "whisper"]), "whisper")

    def test_first_free_engine_when_nothing_saved(self):
        self.assertEqual(default_engine(None, ["openai", "parakeet", "whisper"]), "parakeet")
        self.assertEqual(default_engine(None, ["openai", "whisper"]), "whisper")

    def test_saved_choice_not_available_here(self):
        self.assertEqual(default_engine("parakeet", ["openai", "whisper"]), "whisper")


class ParseEngineChoiceTest(unittest.TestCase):
    options = ["openai", "parakeet", "whisper"]

    def test_enter_picks_default(self):
        self.assertEqual(parse_engine_choice("", self.options, "parakeet"), "parakeet")

    def test_by_number(self):
        self.assertEqual(parse_engine_choice("1", self.options, "parakeet"), "openai")
        self.assertEqual(parse_engine_choice(" 3 ", self.options, "parakeet"), "whisper")

    def test_by_name(self):
        self.assertEqual(parse_engine_choice("Whisper", self.options, "parakeet"), "whisper")

    def test_invalid(self):
        for answer in ("0", "4", "google", "-1"):
            self.assertIsNone(parse_engine_choice(answer, self.options, "parakeet"))


if __name__ == "__main__":
    unittest.main()
