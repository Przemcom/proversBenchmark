import os

# projects current working directory (relative to main.py)
cwd = os.path.dirname(os.path.realpath(f"{__file__}/.."))


class BenchmarkException(Exception):
    pass


class ConfigException(BenchmarkException):
    pass
