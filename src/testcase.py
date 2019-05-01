from dataclasses import dataclass, field
from typing import List


@dataclass
class TestCase:
    name: str
    options: List[str]
    format: str
    input_as_stdin: bool = True
    input_as_last_argument: bool = False
    input_after_option: str = ''
    include_only: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)

    def __post_init__(self):
        pass

