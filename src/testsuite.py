from dataclasses import field, dataclass
from typing import List

from src.testcase import TestCase


@dataclass
class TestSuite:
    name: str
    executable: str
    PATH: str = ''
    version_option: str = ''
    options: List[str] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)

    def verify(self):
        # todo check if executable can be executed with all testcases
        # todo check if all formats can be translated to (static method?) also unify this with Config
        pass


