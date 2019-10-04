from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class InputParser(ABC):
    @staticmethod
    @abstractmethod
    def get_file_input_statistics(file_path: str) -> SATStatistics:
        pass


class OutputParser(ABC):
    @staticmethod
    @abstractmethod
    def parse_output(returncode: int, stdout: Optional[str], stderr: Optional[str]) -> SATStatus:
        pass
