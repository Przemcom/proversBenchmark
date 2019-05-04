import os
import subprocess
import typing

from typing import List, Tuple, Union


def is_executable(executable: str, options: List[str] = None, PATH: str = None) -> typing.NoReturn:
    """Simple check if executable exists
    Not the most efficient implementation (active waiting for timeout)
    :return True if executable exists
    :raise FileNotFound if executable is not found
    """
    command = [executable]
    if options is not None:
        command.extend(options)
    env = os.environ
    if PATH is not None:
        env["PATH"] = PATH + ":" + env["PATH"]

    try:
        subprocess.run(command,
                       timeout=1,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       env=env)
    except subprocess.TimeoutExpired:
        # timeout is not treated as error (executable might wait for input)
        pass
