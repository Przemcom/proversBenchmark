from dataclasses import dataclass
from typing import List

from src.stats import Statistics
from src.test import TestSuite


@dataclass()
class Benchmark:
    test_suite: List[TestSuite]

    def run(self) -> Statistics:
        statistics = Statistics()
        for test_suite in self.test_suite:
            test_suite_stats = test_suite.run()
            statistics.test_suites.append(test_suite_stats)
        return statistics
