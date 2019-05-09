import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("ProverBenchmark")
logger.setLevel(logging.DEBUG)


class BenchmarkException(Exception):
    pass


class ConfigException(BenchmarkException):
    pass
