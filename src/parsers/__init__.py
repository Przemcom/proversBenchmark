from __future__ import annotations

from enum import Enum
from typing import Union, Optional

from src.parsers.input_parsers.tptp_parser import TPTPParser
from src.parsers.output_parsers.prover9_parser import Prover9Parser
from src.parsers.output_parsers.spass_parser import SpassParser


class Formats(Enum):
    TPTP = 'tptp'
    LADR = 'ladr'


class Solvers(Enum):
    PROVER9 = 'prover9'
    SPASS = 'spass'


__format_info_lookup = {
    Formats.TPTP: TPTPParser,
    Formats.TPTP.value: TPTPParser,
    Formats.LADR: None,
    Formats.LADR.value: None,
}


def get_input_parser(format_name: Union[str, Formats]) -> Optional[InputParser]:
    global __format_info_lookup
    key = format_name
    if isinstance(key, str):
        key = format_name.lower()
    return __format_info_lookup.get(key)


__solvers_lookup_table = {
    Solvers.PROVER9: Prover9Parser,
    Solvers.PROVER9.value: Prover9Parser,
    Solvers.SPASS: SpassParser,
    Solvers.SPASS.value: SpassParser,
}


def get_output_parser(solver: Union[str, Solvers]) -> Optional[OutputParser]:
    global __solvers_lookup_table
    key = solver
    if isinstance(key, str):
        key = solver.lower()
    return __solvers_lookup_table.get(key)
