from __future__ import annotations

import json

from src.parsers.parsers import StatisticParser
from src.stats import ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo


class InkresatCNFPTLStatisticParser(StatisticParser):
    """Inkresat conjunctive normal form propositional temporal logic statistic parser"""

    @staticmethod
    def get_file_input_statistics(file_path: str) -> ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo:
        assert file_path.endswith('.json'), 'inkresat parser expects json files for statistics'
        with open(file_path, 'r') as fp:
            dict = json.load(fp)
        return ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo(
            number_of_variables=dict['number_of_variables'],
            number_of_clauses=dict['number_of_clauses'],
            clause_sizes={int(key): int(val) for key, val in dict['clause_sizes'].items()},
            number_of_variables_with_always_connectives=dict['number_of_variables_with_always_connectives'],
            number_of_variables_with_eventually_connectives=dict['number_of_variables_with_eventually_connectives'],
            number_of_variables_without_connective=dict['number_of_variables_without_connective'],
            max_clause_size=dict['max_clause_size']
        )
