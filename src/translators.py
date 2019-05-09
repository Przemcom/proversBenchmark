import os
import subprocess
from dataclasses import dataclass, field
from typing import List

from src import BenchmarkException, cwd, logger
from src._common import is_executable, execute


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

    def __post_init__(self):
        if self.PATH is not None:
            self.PATH = os.path.abspath(os.path.join(cwd, self.PATH))

        if not os.path.isdir(self.PATH):
            raise BenchmarkException(f"PATH '{self.PATH}' is not a directory", self)

    def verify(self):
        """Simple check if executable exists
        todo exception handling may be better
        """
        if self.input_after_option and self.input_as_last_argument:
            raise BenchmarkException("Options input_after_option and input_as_last_argument are mutually exclusive",
                                     self)
        command = [self.executable]
        command.extend(self.options)
        return is_executable(command=command, PATH=self.PATH)

    def translate(self, input_filename: str, output_filename: str) -> subprocess.Popen:
        command = self.get_command(input_filename, output_filename)
        logger.info(f"Translating {input_filename} from {self.from_format} to {self.to_format} to {output_filename}")
        return execute(command=command,
                       input_filename=input_filename,
                       output_filename=output_filename,
                       input_after_option=self.input_after_option,
                       input_as_last_argument=self.input_as_last_argument,
                       output_after_option=self.output_after_option,
                       PATH=self.PATH)

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
