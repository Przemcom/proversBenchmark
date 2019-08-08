# typehint causes circular dependency, fix by importing annotations
# https://stackoverflow.com/questions/33837918/type-hints-solve-circular-dependency
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field, InitVar
from typing import List, ClassVar, Generator, Tuple

import psutil

from src import BenchmarkException, logger
from src._common import execute_monitored
from src.stats import TestSuiteStatistics, TestCaseStatistics, SATStatistics, SATStatus, OutputStatistics, SATType, \
    Serializable
from src.translators import Translator

TEST_CASE_TIMEOUT = 300  # seconds


class CustomPool:
    max_processes = 8

    def __init__(self):
        self.processes = []

    def add(self, proc):
        while len([proc for proc in self.processes if proc.poll() is None]) >= self.max_processes:
            time.sleep(1)
        self.processes.append(proc)

    def wait(self):
        # if any process is running
        while any([proc for proc in self.processes if proc.poll() is None]):
            time.sleep(0.1)


@dataclass
class TestInput(Serializable):
    name: str
    format: str
    cwd: str = os.getcwd()
    path: str = None
    files: List[str] = field(default_factory=list)

    translators: ClassVar[List[Translator]] = []

    cache_path: ClassVar[str] = "inputs"

    def __post_init__(self):
        if self.path is not None and not os.path.isabs(self.path):
            self.path = os.path.abspath(os.path.join(self.cwd, self.path))
        # todo warn if path does not exits

        for file in self.files:
            if not os.path.isfile(os.path.join(self.path, file)):
                raise BenchmarkException(f"file {file} does not exists (is not a file)", self)

    # todo add caching
    def get_file_statistics(self, file_path: str) -> SATStatistics:
        # workaround: look for tptp header
        stats = SATStatistics(name=self.name, path=file_path, format=self.format)

        if self.format != 'TPTP':
            logger.warning(f'no statistics available for format {self.format}. Only TPTP stats are supported')
            return stats

        with open(file_path) as source:
            file_contens = source.read()

            if "cnf(" in file_contens:
                stats.SAT_type = SATType.CNF
            elif "fof(" in file_contens:
                stats.SAT_type = SATType.FOF
            elif "tff(" in file_contens:
                stats.SAT_type = SATType.TFF
            elif "thf(" in file_contens:
                stats.SAT_type = SATType.THF
            else:
                stats.SAT_type = None

            pattern = r'%.*Number of clauses\s*:\s*([0-9]+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_clauses = result.group(1) if result is not None else None

            pattern = r'%.*Number of atoms\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_atoms = result.group(1) if result is not None else None

            pattern = r'%.*Maximal clause size\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.maximal_clause_size = result.group(1) if result is not None else None

            pattern = r'%.*Number of predicates\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_predicates = result.group(1) if result is not None else None

            pattern = r'%.*Number of functors\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_functors = result.group(1) if result is not None else None

            pattern = r'%.*Number of variables\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_variables = result.group(1) if result is not None else None

            pattern = r'%.*Maximal term depth\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.maximal_term_depth = result.group(1) if result is not None else None

        return stats

    # todo add caching
    def as_format(self, desired_format: str) -> Tuple[List[str], List[str], List[Translator]]:
        """Convert self.files to different format
        Cache files will be written to cwd/self._cache_path/self.name/desired_format
        new extension is specified by translator
        :return path to files in specified format and statistics about this file
        """
        if desired_format == self.format:
            return self.files, self.files, []

        # todo support translator chaining
        for translator in TestInput.translators:
            if translator.from_format == self.format and translator.to_format == desired_format:
                break
        else:
            raise BenchmarkException(f"No translator from {self.format} to {desired_format} found")

        pool = CustomPool()
        out_file_paths = []
        translators = []
        for file in self.files:
            in_file_path = os.path.abspath(os.path.join(self.path, file))

            # /cwd/self._cache_path/self.name/desired_format/dir_structure(file)/file.extension
            out_file_path = os.path.join(self.cwd,
                                         TestInput.cache_path,
                                         self.name,
                                         desired_format,
                                         os.path.relpath(file, start=self.path))
            dirname, filename = os.path.split(out_file_path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            extension = '' if translator.extension is None else translator.extension
            out_file_path = os.path.join(dirname, os.path.splitext(filename)[0] + extension)

            proc = translator.translate(in_file_path, out_file_path)
            pool.add(proc)
            out_file_paths.append(out_file_path)
            translators.append(translator)
        pool.wait()
        return self.files, out_file_paths, translators


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
                    test_suite_stats.test_cases.extend(
                        test_case.run(executable=self.executable,
                                      options=self.options,
                                      PATH=self.PATH,
                                      test_input=test_input))
            except BenchmarkException as e:
                logger.error(e)
                continue
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt")
                continue

        yield test_suite_stats


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
        """Get command for this test case"""
        command = [executable]

        if suite_options:
            command.extend(suite_options)

        if self.options:
            command.extend(option for option in self.options if option)

        if self.input_after_option:
            command.append(self.input_after_option)
            command.append(input_filepath)

        if self.input_as_last_argument:
            command.append(input_filepath)

        return command

    def filter_inputs(self, test_inputs: List[TestInput]) -> List[TestInput]:
        """Get inputs that are valid for this test case"""
        result = []
        if not self.include_only and not self.exclude:
            return test_inputs
        elif self.include_only:
            result.extend(test_input for test_input in test_inputs if test_input.name in self.include_only)
        elif self.exclude:
            result.extend(test_input for test_input in test_inputs if test_input.name not in self.include_only)
        return result

    def run(self, executable: str, options: List[str], PATH: str, test_input: TestInput) -> Generator[
        TestCaseStatistics]:
        """Synchronously runs executable with options and self.options against all files in test_input"""
        original_paths, translated_file_paths, translators = test_input.as_format(self.format)
        for original_paths, test_input_path, translator in zip(original_paths, translated_file_paths, translators):
            input_statistics = test_input.get_file_statistics(file_path=original_paths)
            input_statistics.translated_with = translator
            command = self.build_command(executable=executable,
                                         input_filepath=test_input_path,
                                         suite_options=options)
            logger.info(f"Running testcase '{self.name}' with '{test_input_path}': {command}")
            start = time.perf_counter()

            out_stats = OutputStatistics()
            with execute_monitored(command,
                                   stdin=test_input_path,
                                   stdout=os.devnull,
                                   stderr=subprocess.PIPE,
                                   PATH=PATH,
                                   text=True) as proc:
                while proc.poll() is None:
                    time.sleep(0.01)
                    if time.perf_counter() - start > TEST_CASE_TIMEOUT:
                        proc.kill()
                        out_stats.status = SATStatus.TIMEOUT
                        break
                    if psutil.virtual_memory().free < 100 * 1024 * 1024:  # 100MB
                        proc.kill()
                        out_stats.status = SATStatus.OUT_OF_MEMORY
                        break
                    # out_stats.stdout += proc.stdout.read()
                    # out_stats.stderr += proc.stderr.read()
                    # print('comminincated', end=' ')
                out_stats.stdout, out_stats.stderr = proc.communicate()
            test_case_stats = TestCaseStatistics(name=self.name,
                                                 command=command,
                                                 input=input_statistics,
                                                 execution_statistics=proc.get_statistics())

            out_stats.returncode = proc.returncode
            if out_stats.status is not None:
                pass
            elif executable == 'prover9':
                # Prover9: Exit Code	Reason for Termination (from https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/)
                # 0 (MAX_PROOFS) 	The specified number of proofs (max_proofs) was found.
                # 1 (FATAL) 	A fatal error occurred (user's syntax error or Prover9's bug).
                # 2 (SOS_EMPTY) 	Prover9 ran out of things to do (sos list exhausted).
                # 3 (MAX_MEGS) 	The max_megs (memory limit) parameter was exceeded.
                # 4 (MAX_SECONDS) 	The max_seconds parameter was exceeded.
                # 5 (MAX_GIVEN) 	The max_given parameter was exceeded.
                # 6 (MAX_KEPT) 	The max_kept parameter was exceeded.
                # 7 (ACTION) 	A Prover9 action terminated the search.
                # 101 (SIGINT) 	Prover9 received an interrupt signal.
                # 102 (SIGSEGV) 	Prover9 crashed, most probably due to a bug.

                # todo implement parser (if these ifs are not enough)
                # partial prover9 parser
                # prover9 exits with 2 if search failed
                if proc.returncode == 0:
                    out_stats.status = SATStatus.SATISFIABLE
                elif proc.returncode == 1:
                    out_stats.status = SATStatus.ERROR
                elif proc.returncode == 4:
                    out_stats.status = SATStatus.TIMEOUT
                else:
                    out_stats.status = SATStatus.UNSATISFIABLE
            elif executable == 'SPASS':
                if 'SPASS beiseite: Proof found' in out_stats.stdout:
                    out_stats.status = SATStatus.SATISFIABLE
                elif 'SPASS beiseite: Completion found' in out_stats.stdout:
                    out_stats.status = SATStatus.SATISFIABLE

            test_case_stats.output = out_stats

            logger.info(f"Testcase '{self.name}' took "
                        f"{test_case_stats.execution_statistics.execution_time:.2f}, "
                        f"status: {test_case_stats.output.status}, "
                        f"return code: {test_case_stats.output.returncode}")
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
