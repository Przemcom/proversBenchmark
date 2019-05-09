# typehint causes circular dependency, fix by importing annotations
# https://stackoverflow.com/questions/33837918/type-hints-solve-circular-dependency
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, ClassVar, Generator

from src import BenchmarkException, cwd, logger
from src._common import execute
from src.stats import TestSuiteStatistics, TestCaseStatistics, SATStatistics, SATStatus, OutputStatistics
from src.translators import Translator


@dataclass
class TestInput:
    name: str
    format: str
    path: str = None
    files: List[str] = field(default_factory=list)
    files_statistics: SATStatistics = field(default_factory=list)

    translators: ClassVar[List[Translator]] = []

    def __post_init__(self):
        if self.path is not None and not os.path.isabs(self.path):
            self.path = os.path.abspath(os.path.join(cwd, self.path))

        for file in self.files:
            if not os.path.isfile(os.path.join(self.path, file)):
                raise BenchmarkException(f"file {file} does not exists (is not a file)", self)

    def get_file_statistics(self, file: str) -> SATStatistics:
        stats = SATStatistics(name=self.name, format=self.format)
        return stats

    def as_format(self, format: str) -> Generator[str, SATStatistics]:
        # todo return path to file in specific format, translate automatically
        for file in self.files:
            file_path = os.path.abspath(os.path.join(self.path, file))
            stats = self.get_file_statistics(file)
            yield file_path, stats


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

        # todo check if all formats are achievable (static method?) also unify this with Config

    def run(self) -> TestSuiteStatistics:
        test_suite_stats = TestSuiteStatistics(program_name=self.executable,
                                               program_version=self.version)
        for test_case in self.test_cases:
            for test_input in test_case.filter_inputs(self.test_inputs):
                for test_case_stats in test_case.run(executable=self.executable,
                                                     options=self.options,
                                                     PATH=self.PATH,
                                                     test_input=test_input):
                    test_suite_stats.test_cases.append(test_case_stats)

        return test_suite_stats


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

    def build_command(self, executable: str, input_filepath: str, suite_options: List[str] = None) -> List[str]:
        # todo respect self.format (automatically convert)
        command = [executable]

        if suite_options:
            command.extend(suite_options)

        if self.options:
            command.extend(option for option in self.options if option)

        if self.input_after_option:
            command.extend(self.input_after_option)
            command.extend(input_filepath)

        if self.input_as_last_argument:
            command.extend(input_filepath)

        return command

    def filter_inputs(self, test_inputs: List[TestInput]) -> List[TestInput]:
        result = []
        if not self.include_only and not self.exclude:
            return test_inputs
        elif self.include_only:
            result.extend(
                test_input for test_input in test_inputs if test_input.name in self.include_only)
        elif self.exclude:
            result.extend(
                test_input for test_input in test_inputs if test_input.name not in self.include_only)
        return result

    def run(self, executable: str, options: List[str], PATH: str, test_input: TestInput) -> Generator[
        TestCaseStatistics]:
        for input_filepath, input_statistics in test_input.as_format(self.format):
            command = self.build_command(executable=executable,
                                         input_filepath=input_filepath,
                                         suite_options=options)
            # todo ctr+c skips testcase?
            # process may execute too quick to get statistics
            logger.info(f"Running testcase '{self.name}' with '{input_filepath}': {command}")
            with execute(command,
                         stdin=input_filepath,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         PATH=PATH,
                         monitored=True,
                         text=True) as proc:
                while proc.poll() is None:
                    time.sleep(0.05)
            test_case_stats = TestCaseStatistics(name=self.name,
                                                 command=command,
                                                 input=input_statistics,
                                                 execution_statistics=proc.get_statistics())

            out_stats = OutputStatistics(returncode=proc.returncode)
            out_stats.output, out_stats.error = proc.communicate()

            if proc.returncode != 0:
                out_stats.status = SATStatus.ERROR
            else:
                # todo implement parser (if these ifs are not enough)
                # partial prover9 parser
                if 'THEOREM PROVED' in out_stats.output:
                    out_stats.status = SATStatus.SATISFIABLE
                elif 'SEARCH FAILED' in out_stats.output:
                    # todo this case means UNSATISFIABLE or UNKNOWN?
                    out_stats.status = SATStatus.UNSATISFIABLE

            test_case_stats.output = out_stats

            yield test_case_stats
