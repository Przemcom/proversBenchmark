# typehint causes circular dependency, fix by importing annotations
# https://stackoverflow.com/questions/33837918/type-hints-solve-circular-dependency
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import List, ClassVar, Tuple, Optional

from src import BenchmarkException, logger
from src.stats import SATStatistics, SATType, Serializable
from src.translators import Translator


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
            self.path = os.path.realpath(os.path.join(self.cwd, self.path))

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

            # standard TPTP header
            pattern = r'%.*Number of clauses\s*:\s*(\d+).*([\d-]+)\s*unit.*'
            result = re.search(pattern, file_contens)
            stats.number_of_clauses = result.group(1) if result is not None else None
            stats.number_of_unit_clauses = result.group(2) if result is not None else None

            pattern = r'%.*Number of atoms\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_atoms = result.group(1) if result is not None else None

            pattern = r'%.*Maximal clause size\s*:\s*(\d+).*([\d-]+)\s*average.*'
            result = re.search(pattern, file_contens)
            stats.maximal_clause_size = result.group(1) if result is not None else None
            stats.average_clause_size = result.group(2) if result is not None else None

            pattern = r'%.*Number of predicates\s*:\s*(\d+).*([\d-]+)\s*arity.*'
            result = re.search(pattern, file_contens)
            stats.number_of_predicates = result.group(1) if result is not None else None
            stats.predicate_arities = result.group(2) if result is not None else None

            pattern = r'%.*Number of functors\s*:\s*(\d+).*([\d-]+)\s*constant.*([\d-]+)\s*arity.*'
            result = re.search(pattern, file_contens)
            stats.number_of_functors = result.group(1) if result is not None else None
            stats.number_of_constant_functors = result.group(2) if result is not None else None
            stats.functor_arities = result.group(3) if result is not None else None

            pattern = r'%.*Number of variables\s*:\s*(\d+).*([\d-]+)\s*singleton.*'
            result = re.search(pattern, file_contens)
            stats.number_of_variables = result.group(1) if result is not None else None
            stats.number_of_singleton_variables = result.group(2) if result is not None else None

            pattern = r'%.*Maximal term depth\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.maximal_term_depth = result.group(1) if result is not None else None

            # custom TPTP header (from logic formula generator)
            pattern = r'%.*Total number of literals\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.total_number_of_literals = result.group(1) if result is not None else None

            pattern = r'%.*Number of literals\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.number_of_literals = result.group(1) if result is not None else None

            pattern = r'%.*Total functors\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.total_number_of_functors = result.group(1) if result is not None else None

            pattern = r'%.*Total variables\s*:\s*(\d+).*'
            result = re.search(pattern, file_contens)
            stats.total_number_of_variables = result.group(1) if result is not None else None

        return stats

    # todo add caching
    def as_format(self, desired_format: str) -> Tuple[List[str], List[str], List[Optional[Translator]]]:
        """Convert self.files to different format
        Cache files will be written to cwd/self._cache_path/self.name/desired_format
        new extension is specified by translator
        :return path to files in specified format and statistics about this file
        """
        if desired_format == self.format:
            # keep the followwing lists the same size
            return self.files, self.files, [None for _ in self.files]

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


if __name__ == '__main__':
    ti = TestInput(name='tmp',
                   format='TPTP',
                   path='/home/mat/studia-repos/studio-projektowe/logit-formula-generator/test_data/',
                   files=['data_set1_100_2-nowy.p'])
    stat = ti.get_file_statistics(
        file_path='/home/mat/studia-repos/studio-projektowe/logit-formula-generator/test_data/data_set1_100_2-nowy.p'
    )
    print(stat)
