from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Generator

import psutil

from src import BenchmarkException, logger
from src.benchmark import Benchmark
from src.parsers import get_output_parser
from src.stats import TestCaseStatistics, SATStatus, OutputStatistics, MonitoredProcess
from src.tests.non_blocking_stream_reader import NonBlockingStreamReader
from src.tests.test_input import TestInput


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
        logger.info(f'Running testcase {self.name}')
        original_paths, translated_file_paths, translators = test_input.as_format(self.format)
        for original_paths, test_input_path, translator in zip(original_paths, translated_file_paths, translators):
            input_statistics = test_input.get_file_statistics(file_path=original_paths)
            input_statistics.translated_with = translator
            command = self.build_command(executable=executable, input_filepath=test_input_path, suite_options=options)
            logger.info(f'Executing {command}')

            out_stats = OutputStatistics()
            env = os.environ
            if PATH:
                env['PATH'] = PATH + ':' + env['PATH']
            start = time.perf_counter()
            with MonitoredProcess(command, stdin=open(test_input_path, 'r'), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, env=env, text=True) as proc:
                nbsr_stdout = NonBlockingStreamReader(stream=proc.stdout)
                nbsr_stderr = NonBlockingStreamReader(stream=proc.stderr)
                last_read = time.time()
                while proc.poll() is None:
                    time.sleep(0.01)
                    if time.perf_counter() - start > Benchmark.test_case_timeout:
                        proc.kill()
                        out_stats.status = SATStatus.TIMEOUT
                        break
                    if psutil.virtual_memory().free < 100 * 1024 * 1024:  # 100MB
                        proc.kill()
                        out_stats.status = SATStatus.OUT_OF_MEMORY
                        break
                    # print(f'looping {last_read} {time.time()}')
                    if time.time() - last_read > 1:
                        if command[0] != 'prover9':
                            out_stats.stdout = ''.join(nbsr_stdout.readall())
                        out_stats.stderr = ''.join(nbsr_stderr.readall())
                        last_read = time.time()
                # make sure you read everything
                out_stats.stdout += ''.join(nbsr_stdout.readall())
                out_stats.stderr += ''.join(nbsr_stderr.readall())

            test_case_stats = TestCaseStatistics(name=self.name, command=command, input=input_statistics,
                                                 execution_statistics=proc.get_statistics())

            out_stats.returncode = proc.returncode
            if out_stats.status is not None:
                pass
            else:
                parser = get_output_parser(solver=executable)
                if parser:
                    out_stats.status = parser.parse_output(returncode=out_stats.returncode, stdout=out_stats.stdout,
                                                           stderr=out_stats.stderr)
                else:
                    logger.warning('There is no parser to set output SAT status TODO')
                    out_stats.status = SATStatus.UNKOWN
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
