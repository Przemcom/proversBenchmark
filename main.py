import argparse
import json

from src import logger
from src.benchmark import Benchmark
from src.config import Config
from src.stats import SerializableJSONEncoder
from src.test import TestInput


def parse_args():
    parser = argparse.ArgumentParser(prog="Provers Benchmark",
                                     description="Benchmark for testing provers")
    parser.add_argument("-v", "--version", action="version",
                        version="%(prog)s Pre-alpha 0.1",
                        help="Prints current version")
    parser.add_argument("-f", "--file", default="config.toml", help="config file")

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    config = Config(config_file=args.file)
    config.load_config()
    inputs = len(config.test_inputs)
    translators = len(TestInput.translators)
    files = sum(len(test_inputs.files) for test_inputs in config.test_inputs)
    test_suites = len(config.test_suites)
    test_cases = sum(len(test_suite.test_cases) for test_suite in config.test_suites)
    logger.info(
        f'Starting with {inputs} inputs, {translators} translators, {files} files, {test_suites} test suites, {test_cases} test cases')

    benchmark = Benchmark(test_suite=config.test_suites)
    stats = benchmark.run()
    with open(config.output_dir, 'w') as outfile:
        logger.info(f'writing results to {config.output_dir}')
        json.dump(stats, outfile, indent=2, cls=SerializableJSONEncoder)
