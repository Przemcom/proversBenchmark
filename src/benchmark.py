from dataclasses import dataclass
from typing import List

from src import logger
from src.stats import Statistics, SATStatus
from src.test import TestSuite


@dataclass
class Benchmark:
    test_suite: List[TestSuite]

    def run(self) -> Statistics:
        statistics = Statistics()
        for test_suite in self.test_suite:
            test_suite_stats = test_suite.run()
            statistics.test_suites.extend(test_suite_stats)

        unsat = 0
        sat = 0
        timeout = 0
        different = 0
        for test_suite in statistics.test_suites:
            for test_case in test_suite.test_cases:
                if test_case.output.status == SATStatus.TIMEOUT:
                    timeout += 1
                if test_case.output.status == SATStatus.SATISFIABLE:
                    sat += 1
                if test_case.output.status == SATStatus.UNSATISFIABLE:
                    unsat += 1
                else:
                    different += 1
        logger.info(f'{sat} tests were satisfiable, {unsat} were unsat, {timeout} were timeout, '
                    f'{different} ended with different status')

        return statistics
