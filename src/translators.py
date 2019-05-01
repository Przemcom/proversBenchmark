from dataclasses import dataclass


@dataclass(frozen=True)
class Translator:
    from_format: str
    to_format: str
    executable: str
    path: str = "."

    def verify(self):
        # todo check if executable can be executed
        pass

    def translate(self, text) -> str:
        """Translate text to different syntax
        return translated text
        """
        # TODO: deufalt implementation: call executable
        pass
