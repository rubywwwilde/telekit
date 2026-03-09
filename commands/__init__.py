from importlib import import_module

__all__ = ["IngGPTCommand", "IngTranscribeCommand"]


def __getattr__(name):
    if name == "IngGPTCommand":
        return import_module("commands.ing_gpt").IngGPTCommand
    if name == "IngTranscribeCommand":
        return import_module("commands.ing_transcribe.ing_transcribe").IngTranscribeCommand
    raise AttributeError(name)
