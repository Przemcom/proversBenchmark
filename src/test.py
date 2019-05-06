# typehint causes circular dependency, fix by importing annotations
# https://stackoverflow.com/questions/33837918/type-hints-solve-circular-dependency
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from typing import List
from typing import TYPE_CHECKING

from src import BenchmarkException, cwd
from src.common import is_executable
from src.testinput import TestInput

@dataclass
class TestSuite:
    name: str
    executable: str
    PATH: str = None
    version: str = None
    options: List[str] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)
    test_inputs: List[TestInput] = field(default_factory=list)

    def __post_init__(self):
        if self.PATH is not None and not os.path.isabs(self.PATH):
            self.PATH = os.path.abspath(os.path.join(cwd, self.PATH))

    def verify(self):
        is_executable(command=[self.executable], PATH=self.PATH)

        # todo check if all formats are achievable (static method?) also unify this with Config


@dataclass
class TestCase:
    name: str
    options: List[str]
    format: str
    input_after_option: str = None
    input_as_last_argument: bool = False
    include_only: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.input_after_option and self.input_as_last_argument:
            raise BenchmarkException("input_after_option and input_as_last_argument are mutually exclusive",
                                     self)

        if self.exclude and self.include_only:
            raise BenchmarkException(f"exclude and include_only are mutually exclusive", self)

    def verify(self, test_suite: TestSuite):
        """Dry run: check if all arguments can be executed"""
        # todo implement. It is hard, because we must generate everything to verify
        test_inputs = []
        if not self.include_only and not self.exclude:
            test_inputs = test_suite.test_inputs
        elif self.include_only:
            test_inputs.extend(test_input for test_input in test_suite.test_inputs if test_input.name in self.include_only)
        elif self.exclude:
            test_inputs.extend(test_input for test_input in test_suite.test_inputs if test_input.name not in self.include_only)

        if not test_inputs:
            raise BenchmarkException("no input defined for this testcase", test_suite, self)

        env = os.environ.copy()
        if test_suite.PATH is not None:
            env["PATH"] = test_suite.PATH + ":" + env["PATH"]

        # no need to test all inputs, just pick one
        test_input = test_inputs[0]

        command = self.build_command(test_suite.executable, test_input, test_suite.options)
        try:
            is_executable(command, PATH=test_suite.PATH)
        except FileNotFoundError as e:
            # should not happen at this point, should have been checked in test suite
            raise BenchmarkException(f"Command not found: {command}", test_suite, self)

    def build_command(self, executable: str, test_input: TestInput, suite_options: List[str] = None) -> List[str]:
        # todo respect self.format (automatically convert)
        command = [executable]

        if suite_options:
            command.extend(suite_options)

        if self.options:
            command.extend(option for option in self.options if option)

        if self.input_after_option:
            command.extend(self.input_after_option)
            command.extend(test_input.as_format(self.format))

        if self.input_as_last_argument:
            command.extend(test_input.as_format(self.format))

        return command
