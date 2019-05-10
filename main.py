import argparse
import json

from src.benchmark import Benchmark
from src.config import Config
from src.stats import SerializableJSONEncoder


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
    print(json.dumps(stats, indent=2, cls=SerializableJSONEncoder))
