import os
from dataclasses import dataclass, field
from typing import List, ClassVar

from src.translators import Translator


@dataclass
class TestInput:
    name: str
    format: str
    path: str = "."
    files: List[str] = field(default_factory=list)

    translators: ClassVar[List[Translator]] = []

    def verify(self):
        for file in self.files:
            if os.path.isfile(os.path.join(self.path, file)):
                print(f"file {file} does not exists (is not a file)")
