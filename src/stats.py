import datetime
import json
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List

import psutil


class SerializableJSONEncoder(json.JSONEncoder):
    """This encoder can encode Enum and classes that inherit Serializable
    Usage json.dumps(variable, cls=SerializableJSONEncoder)
    """

    def default(self, o):
        if isinstance(o, Serializable):
            return o.as_plain_dict()
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class Serializable:
    def as_plain_dict(self):
        """Convert to dict that holds only basic types"""
        # todo ignore variables that start with _
        class_dict = self.__dict__.copy()
        for key, value in self.__dict__.items():
            if key.startswith('_') or key.startswith(self.__class__.__name__):
                class_dict.pop(key)
        return class_dict


@dataclass
class ExecutionStatistics(Serializable):
    # todo which cpu times do we need?
    cpu_time = None
    execution_time: float = 0
    peak_memory: int = None
    disk_reads: int = None
    disk_writes: int = None

    def update(self, proc: psutil.Process):
        try:
            io_counters = proc.io_counters()
            self.disk_reads = io_counters.read_bytes + io_counters.read_chars
            self.disk_writes = io_counters.write_bytes + io_counters.read_chars
        except psutil.AccessDenied:
            pass

        mem_info = proc.memory_info()
        if self.peak_memory is None or self.peak_memory < mem_info.rss:
            self.peak_memory = mem_info.rss

        self.cpu_time = proc.cpu_times()


class MonitoredProcess(subprocess.Popen):
    """Start process that can be monitored by periodic calling poll() in active loop
    Note that:
    poll() must be called at least once to get proper statistics
    short running process can exit before poll method was executed
    use with context manager to auto stop execution time
    """

    def __init__(self, *args, **kwargs):
        self.exec_stats = ExecutionStatistics()
        super().__init__(*args, **kwargs)
        self._start = time.perf_counter()
        self.proc = psutil.Process(self.pid)
        self.poll()

    def poll(self):
        if super().poll() is not None:
            return super().poll()

        # can not do it in __exit__, because process no longer not exists there
        self.exec_stats.update(self.proc)

        return None

    def stop(self):
        """If not used with contex manager, stop counting execution time"""
        self.__exit__(None, None, None)

    def get_statistics(self) -> ExecutionStatistics:
        """Return gathered statistics"""
        return self.exec_stats

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exec_stats.execution_time = time.perf_counter() - self._start


class SATType(Enum):
    FOF = "First-order Formula"
    CNF = "Conjunctive Normal Form"
    TFF = "Typed First-order Formula"
    THF = "Typed Higher-order Formula"


@dataclass
class CPUStatistics(Serializable):
    name: str = platform.processor()
    min_frequency: float = psutil.cpu_freq().min
    max_frequency: float = psutil.cpu_freq().max
    logical_threads: int = psutil.cpu_count(logical=True)
    physical_threads: int = psutil.cpu_count(logical=False)


@dataclass
class HardwareStatistics(Serializable):
    system: str = platform.system()
    release: str = platform.release()
    version: str = platform.version()
    cpu: CPUStatistics = CPUStatistics()
    total_memory: int = psutil.virtual_memory().total


@dataclass
class SATStatistics(Serializable):
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
class SATStatus(Enum):
    ERROR = "error"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    UNKOWN = "unknown"
    TIMEOUT = "timeout"
    OUT_OF_MEMORY = "out of memory"


@dataclass
class OutputStatistics(Serializable):
    returncode: int = None
    status: SATStatus = None
    stderr: str = None
    stdout: str = None


@dataclass
class TestCaseStatistics(Serializable):
    name: str
    command: List[str]
    execution_statistics: ExecutionStatistics = None
    input: SATStatistics = None
    output: OutputStatistics = None


@dataclass
class TestSuiteStatistics(Serializable):
    program_name: str
    program_version: str
    test_cases: List[TestCaseStatistics] = field(default_factory=list)


@dataclass
class Statistics(Serializable):
    def as_plain_dict(self):
        dict_copy = self.__dict__.copy()
        dict_copy["date"] = str(self.date)
        return dict_copy

    test_suites: List[TestSuiteStatistics] = field(default_factory=list)
    date: datetime.datetime = datetime.datetime.now()
    hardware: HardwareStatistics = HardwareStatistics()


if __name__ == '__main__':
    import functools

    proc = functools.partial(MonitoredProcess, ['sleep', '5'])
    with proc() as running_process:
        while running_process.poll():
            time.sleep(0.1)

    stats = running_process.get_statistics()
    test_case_stats = TestCaseStatistics(name="test",
                                         command=["ps", "-aux"],
                                         execution_statistics=stats,
                                         input=SATStatistics())
    print(json.dumps(test_case_stats, default=SerializableJSONEncoder))
