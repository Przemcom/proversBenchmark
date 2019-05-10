import os
import subprocess
from typing import List, Union, IO, Any

from src.stats import MonitoredProcess


def execute(command: List[str],
            stdin: Union[str, int, IO[Any]] = subprocess.DEVNULL,
            stdout: Union[str, int, IO[Any]] = subprocess.DEVNULL,
            stderr: Union[str, int, IO[Any]] = subprocess.DEVNULL,
            PATH: str = None,
            monitored: bool = False,
            *args, **kwargs) -> Union[subprocess.Popen, MonitoredProcess]:
    """Execute command is subprocess
    is stdin, stdout, stderr is str, then opens file
    PATH is appended to enviroment variable and passed to Popen as env
    args and kwargs are passed to Popen
    :return running process: MonitoredProcess if monitored == True else Popen
    """
    if isinstance(stdin, str):
        stdin = open(stdin, 'r')
    if isinstance(stdout, str):
        stdout = open(stdout, 'w')
    if isinstance(stderr, str):
        stderr = open(stderr, 'w')

    env = os.environ
    if PATH is not None:
        env["PATH"] = PATH + ":" + env["PATH"]

    if monitored:
        return MonitoredProcess(command,
                                stdin=stdin,
                                stdout=stdout,
                                stderr=stderr,
                                env=env,
                                *args,
                                **kwargs)
    else:
        return subprocess.Popen(command,
                                stdin=stdin,
                                stdout=stdout,
                                stderr=stderr,
                                env=env,
                                *args,
                                **kwargs)
