# typehint causes circular dependency, fix by importing annotations
# https://stackoverflow.com/questions/33837918/type-hints-solve-circular-dependency
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field, InitVar
from typing import List, ClassVar, Generator

from src import BenchmarkException, logger
from src._common import execute
from src.stats import TestSuiteStatistics, TestCaseStatistics, SATStatistics, SATStatus, OutputStatistics
from src.translators import Translator


@dataclass
class TestInput:
    name: str
    format: str
    cwd: str = os.getcwd()
    path: str = None
    files: List[str] = field(default_factory=list)

    translators: ClassVar[List[Translator]] = []

    def __post_init__(self):
        if self.path is not None and not os.path.isabs(self.path):
            self.path = os.path.abspath(os.path.join(self.cwd, self.path))

        for file in self.files:
            if not os.path.isfile(os.path.join(self.path, file)):
                raise BenchmarkException(f"file {file} does not exists (is not a file)", self)

    def get_file_statistics(self, file_path: str) -> SATStatistics:
        stats = SATStatistics(name=self.name, path=file_path, format=self.format)
        return stats

    def as_format(self, desired_format: str) -> Generator[str, SATStatistics]:
        if desired_format == self.format:
            for file in self.files:
                file_path = os.path.abspath(os.path.join(self.path, file))
                stats = self.get_file_statistics(file_path=file_path)
                yield file_path, stats
                return

        # todo support translator chining
        for translator in TestInput.translators:
            if translator.from_format == self.format and translator.to_format == desired_format:
                break
        else:
            raise BenchmarkException(f"No translator from {self.format} to {desired_format} found")

        extension = os.path.splitext(self.files[0])[1] if translator.extension is None else translator.extension
        for file in self.files:
            in_file_path = os.path.abspath(os.path.join(self.path, file))
            out_file_path = self._get_out_filepath(desired_format, file, extension)
            translator.translate(in_file_path, out_file_path).wait()
            yield out_file_path, self.get_file_statistics(file_path=out_file_path)

    def _get_out_filepath(self, prefix: str, file: str, extension: str):
        out_dir = os.path.join(self.cwd, "inputs", self.name, prefix)
        directory_from_file, filename = os.path.split(file)
        directory_from_file = os.path.join(out_dir, directory_from_file)
        if not os.path.exists(directory_from_file):
            os.makedirs(directory_from_file)
        return os.path.join(directory_from_file, os.path.splitext(file)[0] + extension)


@dataclass
class TestSuite:
    name: str
    executable: str
    cwd: InitVar[str] = os.getcwd()
    PATH: str = None
    version: str = None
    options: List[str] = field(default_factory=list)
    cache_dir: str = "test-inputs"
    test_cases: List[TestCase] = field(default_factory=list)
    test_inputs: List[TestInput] = field(default_factory=list)

    def __post_init__(self, cwd):
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


if __name__ == '__main__':
    input = TestInput(name="tmp ",
                      format="TPTP",
                      path="../../TPTP-v7.2.0",
                      files=["example.p"])
    translator = Translator(from_format="TPTP",
                            to_format="LADR",
                            executable="tptp_to_ladr",
                            extension="in",
                            PATH="../../provers/LADR-2009-11A/bin")
    TestInput.translators.append(translator)
    # translator.translate(input_filename="../../TPTP-v7.2.0/example.p", output_filename="example_converted.in")
    for i in input.as_format("LADR"):
        print(i)
