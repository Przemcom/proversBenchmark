import os
import subprocess
from dataclasses import dataclass, field
from typing import List

from src import BenchmarkException
from src.common import is_executable


@dataclass
class Translator:
    """Translate text to different syntax by calling executable
    by default input file is piped to stdin, stdout is piped to output file
    command is composed as follows:
    executable [options] [input_after_option input_filename] [output_output_after_option out_filename]
    if input_as_last_argument is True, input_filename will be last arguments
    input_as_last_argument and input_after_option are mutually exclusive
    """
    from_format: str
    to_format: str
    executable: str
    options: List[str] = field(default_factory=list)
    input_after_option: str = None
    input_as_last_argument: bool = False
    output_after_option: str = None
    PATH: str = None

    def verify(self):
        """Simple check if executable exists
        todo exception handling may be better
        """
        if self.input_after_option and self.input_as_last_argument:
            raise BenchmarkException("Options input_after_option and input_as_last_argument are mutually exclusive")
        return is_executable(executable=self.executable, PATH=self.PATH)

    def translate(self, input_filename: str, output_filename: str) -> subprocess.Popen:
        command = self.get_command(input_filename, output_filename)
        stdin = subprocess.DEVNULL
        stdout = subprocess.DEVNULL
        stderr = subprocess.DEVNULL
        if not self.output_after_option or not self.input_as_last_argument:
            stdout = open(output_filename, 'w')
        if not self.input_after_option:
            stdin = open(input_filename, 'r')

        env = os.environ
        if self.PATH is not None:
            env["PATH"] = self.PATH + ":" + env["PATH"]

        return subprocess.Popen(command,
                                stdin=stdin,
                                stdout=stdout,
                                stderr=stderr,
                                env=env)

    def get_command(self, input_filename: str, output_filename: str) -> List[str]:
        command = [self.executable]
        command.extend(self.options)
        if self.input_after_option:
            command.append(self.input_after_option)
            command.append(input_filename)

        if self.output_after_option:
            command.append(self.output_after_option)
            command.append(output_filename)

        if self.input_as_last_argument:
            command.append(input_filename)
        return command


if __name__ == '__main__':
    t = Translator(from_format="TPTP",
                   to_format="LADR",
                   executable="cat",
                   )
    v = t.verify()
    print(v)
    # t.translate('common.py', 'tmp.txt')
