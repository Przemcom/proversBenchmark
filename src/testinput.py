import os
from dataclasses import dataclass, field, InitVar
from typing import List, ClassVar

from src import BenchmarkException, cwd
from src.translators import Translator


@dataclass
class TestInput:
    name: str
    format: str
    path: str = None
    files: List[str] = field(default_factory=list)

    translators: ClassVar[List[Translator]] = []

    def __post_init__(self):
        if self.path is not None and not os.path.isabs(self.path):
            self.path = os.path.abspath(os.path.join(cwd, self.path))

    def verify(self):
        for file in self.files:
            if not os.path.isfile(os.path.join(self.path, file)):
                raise BenchmarkException(f"file {file} does not exists (is not a file)", self)

    def as_format(self, format: str) -> str:
        # todo return path to file in specific format, translate automatically
        return os.path.join(self.path, self.name)
