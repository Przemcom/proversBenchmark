import datetime
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List

import psutil as psutil


@dataclass
class ExecutionStatistics:
    pid: int
    cpu_time = None
    execution_time: int = 0
    peak_memory: int = 0
    peak_disk_read: int = 0
    peak_disk_write: int = 0


class MonitoredProcess(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        # todo which cpu times do we need?
        self.cpu_time = None
        self.execution_time = None
        self.peak_memory = 0
        self._has_permission = True
        try:
            psutil.Process().io_counters()
            self.disk_reads = 0
            self.disk_writes = 0
        except psutil.AccessDenied:
            # must me sudo to get disk io info
            self._has_permission = False
            self.disk_reads = None
            self.disk_writes = None

        super().__init__(*args, **kwargs)
        self.proc = psutil.Process(self.pid)
        self._start = time.time()
        self.poll()

    def __enter__(self):
        self.disk_reads = 0
        self.disk_writes = 0
        self.peak_memory = 0
        return self

    def poll(self):
        if super().poll() is not None:
            return super().poll()

        # can not do it in __exit__, because process no longer not exits there
        if self._has_permission:
            io_counters = self.proc.io_counters()
            self.disk_reads = io_counters.read_bytes + io_counters.read_chars
            self.disk_writes = io_counters.write_bytes + io_counters.read_chars

        mem_info = self.proc.memory_info()
        if self.peak_memory < mem_info.rss:
            self.peak_memory = mem_info.rss

        self.cpu_time = self.proc.cpu_times()
        return None

    def stop(self):
        self.__exit__(None, None, None)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.execution_time = time.time() - self._start


class SATType(Enum):
    FOF = "First-order Formula"
    CNF = "Conjunctive Normal Form"
    TFF = "Typed First-order Formula"
    THF = "Typed Higher-order Formula"


@dataclass
class CPUStatistics:
    name: str = platform.processor()
    min_frequency: float = psutil.cpu_freq().min
    max_frequency: float = psutil.cpu_freq().max
    logical_threads: int = psutil.cpu_count(logical=True)
    physical_threads: int = psutil.cpu_count(logical=False)


@dataclass
class HardwareStatistics:
    system: str = platform.system()
    release: str = platform.release()
    version: str = platform.version()
    cpu: CPUStatistics = CPUStatistics()
    total_memory: int = psutil.virtual_memory().total


@dataclass
class SATStatistics:
    name: str = None
    path: str = None
    # list of commands used to translate
    translated_with: List[List[str]] = field(default_factory=list)
    SAT_type: SATType = None
    format: str = None
    number_of_clauses: int = None
    number_of_atoms: int = None
    maximal_clause_size: int = None
    number_of_predicates: int = None
    number_of_functors: int = None
    number_of_variables: int = None
    maximal_term_depth: int = None


@dataclass
class SATStatus:
    ERROR = "error"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    UNKOWN = "UNKNOWN"


@dataclass
class OutputStatistics:
    returncode: int = None
    status: SATStatus = None
    error: str = None
    output: str = None


@dataclass
class TestCaseStatistics:
    name: str
    command: List[str]
    execution_time: int = None
    # todo add type hint
    cpu_time = None
    peak_memory = 0
    disk_writes = 0
    disk_reads = 0

    input: SATStatistics = None
    output: OutputStatistics = None


@dataclass
class TestSuiteStatistics:
    program_name: str
    program_version: str
    test_cases: List[TestCaseStatistics] = field(default_factory=list)


@dataclass
class Statistics:
    test_suites: List[TestSuiteStatistics] = field(default_factory=list)
    date: datetime.datetime = datetime.datetime.now()
    hardware: HardwareStatistics = HardwareStatistics()
