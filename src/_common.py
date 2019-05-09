import os
import subprocess
import typing
from typing import List

from src import BenchmarkException


def is_executable(command: List[str],
                  check_return_code: bool = False,
                  PATH: str = None) -> typing.NoReturn:
    """Simple check if executable exists
    Not the most efficient implementation (active waiting for timeout)
    """
    env = os.environ.copy()
    if PATH is not None:
        env["PATH"] = PATH + ":" + env["PATH"]

    try:
        subprocess.run(command,
                       timeout=1,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       check=check_return_code,
                       env=env)
    except subprocess.TimeoutExpired:
        # timeout is not treated as error (executable might wait for input)
        pass
    except FileNotFoundError as e:
        raise BenchmarkException(f"Executable not found {e.filename}", command)
    except subprocess.CalledProcessError as e:
        raise BenchmarkException(f"Command exits non zero: {command}")


def execute(command: List[str],
            input_filename: str,
            output_filename: str,
            input_after_option: str = None,
            input_as_last_argument: str = None,
            output_after_option: str = None,
            PATH: str = None):
    stdin = subprocess.DEVNULL
    stdout = subprocess.DEVNULL
    stderr = subprocess.DEVNULL
    if not output_after_option:
        stdout = open(output_filename, 'w')
    if not input_after_option and not input_as_last_argument:
        stdin = open(input_filename, 'r')

    env = os.environ
    if PATH is not None:
        env["PATH"] = PATH + ":" + env["PATH"]

    return subprocess.Popen(command,
                            stdin=stdin,
                            stdout=stdout,
                            stderr=stderr,
                            env=env)
