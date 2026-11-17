"""Pure helpers for choosing a transcription engine.

Nothing here touches the filesystem, the network or a subprocess.
"""

ENGINES = {
    "openai": "OpenAI Whisper API (paid, needs an API key)",
    "parakeet": "NVIDIA Parakeet, runs on this Mac (free, Apple Silicon only)",
    "whisper": "Whisper, runs on this computer (free, slower)",
}
FREE_ENGINES = ("parakeet", "whisper")


def available_engines(system, machine):
    """Engines that can run on this machine (platform.system() / platform.machine())."""
    # parakeet-mlx runs on Apple's MLX framework, which needs Apple Silicon.
    apple_silicon = system == "Darwin" and machine == "arm64"
    return [e for e in ENGINES if e != "parakeet" or apple_silicon]


def engine_from_config(config):
    """Return the engine saved in the transcriber config, or None.

    Configs written before engines existed only hold an OpenAI key.
    """
    engine = config.get("engine")
    if engine in ENGINES:
        return engine
    if engine is None and config.get("openai_key"):
        return "openai"
    return None


def default_engine(saved, options):
    """The saved engine if it can run here, otherwise the first free one."""
    if saved in options:
        return saved
    return next(e for e in options if e in FREE_ENGINES)


def parse_engine_choice(answer, options, default):
    """Turn a menu answer (number, name or empty) into an engine, or None if invalid."""
    answer = answer.strip().lower()
    if not answer:
        return default
    if answer.isdigit() and 1 <= int(answer) <= len(options):
        return options[int(answer) - 1]
    return answer if answer in options else None
