# proversBenchmark

This project is designed to benchmark SAT solvers like prover9, spass...

In general it calls arbitrary command with specified options with inputs specified as file

## Usage

Specify benchmark configurations in `config.toml`:

- inputs - set of files in one format (currently only tptp format is supported). Input file can be provided via stdin, after options, as last argument
- translators - optional - executable used to automatically translate input file to different format. Cached files are written to `inputs` folder
- test suite - list of testcases with common executable
- test case - executable with specified command line options

See `config.toml` for detail option description

## Install

Minimum python 3.7

```bash
pip -r requirements.txt
```

## Run

```bash
python main.py
```

Get help with `python main.py -h`