import argparse
from pprint import pprint

from src.benchmark import Benchmark
from src.config import Config


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

    benchmark = Benchmark(test_suite=config.test_suites)
    print("Result: ")
    stats = benchmark.run()
    for testcase in stats.test_suites[0].test_cases:
        print("testCase: ", end='')
        pprint(testcase.__dict__)
    print(stats.hardware)
