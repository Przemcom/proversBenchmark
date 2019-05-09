import logging
import os

# projects current working directory (relative to main.py)
cwd = os.path.dirname(os.path.realpath(f"{__file__}/.."))

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("ProverBenchmark")
logger.setLevel(logging.DEBUG)


class BenchmarkException(Exception):
    pass


class ConfigException(BenchmarkException):
    pass
