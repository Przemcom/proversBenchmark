import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("ProverBenchmark")
logger.setLevel(logging.DEBUG)
hdlr = logging.FileHandler('benchmark.log')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)


class BenchmarkException(Exception):
    pass


class ConfigException(BenchmarkException):
    pass
