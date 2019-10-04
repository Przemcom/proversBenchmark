from __future__ import annotations

import re

from src.parsers._parsers import InputParser
from src.stats import SATStatistics, SATType


class TPTPParser(InputParser):
    @staticmethod
    def get_file_input_statistics(file_path: str) -> SATStatistics:
        stats = SATStatistics(path=file_path, format='tptp')

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
