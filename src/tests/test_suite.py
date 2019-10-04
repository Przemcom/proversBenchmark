from __future__ import annotations

import os
from dataclasses import dataclass, field, InitVar
from typing import List

from src import BenchmarkException, logger
from src.stats import TestSuiteStatistics
from src.tests.test_input import TestInput


@dataclass
class TestSuite:
    name: str
    executable: str
    cwd: InitVar[str] = os.getcwd()
    PATH: str = None
    version: str = None
    options: List[str] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)
    test_inputs: List[TestInput] = field(default_factory=list)

    def __post_init__(self, cwd):
        if self.PATH is not None and not os.path.isabs(self.PATH):
            self.PATH = os.path.abspath(os.path.join(cwd, self.PATH))

        # todo warn if PATH does not exits
        # todo check if all formats are achievable (static method?) also unify this with Config

    def run(self) -> TestSuiteStatistics:
        """Synchronously run all test cases defined in this test suite"""
        test_suite_stats = TestSuiteStatistics(program_name=self.executable,
                                               program_version=self.version)
        for test_case in self.test_cases:
            try:
                for test_input in test_case.filter_inputs(self.test_inputs):
                    test_case_stats = test_case.run(executable=self.executable,
                                                    options=self.options,
                                                    PATH=self.PATH,
                                                    test_input=test_input)
                    test_suite_stats.test_cases.extend(test_case_stats)
            except BenchmarkException as e:
                logger.error(e)
                continue
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt")
                continue

        yield test_suite_stats
