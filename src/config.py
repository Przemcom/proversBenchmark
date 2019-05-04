import copy
import glob
import logging
import os
from dataclasses import dataclass, field
from functools import wraps
from pprint import pprint
from typing import List, Dict, Type

import toml

from src import BenchmarkException, ConfigException
from src.testcase import TestCase
from src.testinput import TestInput
from src.testsuite import TestSuite
from src.translators import Translator

logging.basicConfig(level=logging.INFO)


@dataclass
class Config:
    config_file: str = "config.toml"
    output_dir: str = "benchmark-output"
    log_file: str = "benchmark.log"
    test_inputs: List[TestInput] = field(default_factory=list)
    test_suites: List[TestSuite] = field(default_factory=list)

    _load_errors_occured: bool = False
    _logger: logging.Logger = logging.getLogger("Config")

    _log_scope: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._logger.setLevel(logging.INFO)

    class Decorators:
        """Contains decorators specific for Config"""
        pass

        @staticmethod
        def log_scope(message):
            """Decorate to indicate what part of config is being parsed, ex. testInput
            used for logging
            stored as stack
            """

            def log_scope_decorator(func):
                @wraps(func)
                def wrapper(self, *args, **kwargs):
                    self._log_scope.append(message)
                    result = func(self, *args, **kwargs)
                    self._log_scope.pop()
                    return result

                return wrapper

            return log_scope_decorator

    def load_config(self):
        """Load and verify config"""
        self._load_errors_occured = False
        if not os.path.isfile(self.config_file):
            self._logger.error(f"Config file '{self.config_file}'' is not found/not a file")
            return

        self._logger.info(f"Reading {self.config_file}")
        with open(self.config_file) as source:
            benchmark_config = toml.load(source)

        self._load_general(benchmark_config)
        self._load_translators(benchmark_config)
        self._load_test_inputs(benchmark_config)
        self._load_test_suites(benchmark_config)

        if benchmark_config:
            self.log_unknown_keys(benchmark_config)

        if self._load_errors_occured:
            self.test_inputs.clear()
            TestInput.translators.clear()
            self.test_suites.clear()
            raise ConfigException("Errors occured in config. see log warnings and errors")

    @Decorators.log_scope("general")
    def _load_general(self, config: Dict):
        general_config = config.pop("general", None)
        if general_config is None:
            return

        # used for logging only
        general_config_copy = copy.deepcopy(general_config)

        error_occured = False
        self.log_file, ok = self._pop_key(source=general_config,
                                          variable="log_file",
                                          context=general_config_copy,
                                          default=self.log_file,
                                          required=False,
                                          type_check=str)
        error_occured |= not ok

        self.output_dir, ok = self._pop_key(source=general_config,
                                            variable="output_dir",
                                            context=general_config_copy,
                                            default=self.output_dir,
                                            required=False,
                                            type_check=str)
        error_occured |= not ok
        # todo check is is writeable (should be dir or file?

        if general_config:
            self.log_unknown_keys(general_config, general_config_copy)

    @Decorators.log_scope("translators")
    def _load_translators(self, config: Dict):
        # todo: handle multiple translators for one format
        translators_config, ok = self._pop_key(source=config,
                                               variable="translators",
                                               context=config,
                                               required=True,
                                               type_check=list)

        if not ok:
            return

        for translator_config in translators_config:
            # for error reporting
            translator_config_copy = copy.deepcopy(translator_config)

            error_occured = False
            from_format, ok = self._pop_key(source=translator_config,
                                            variable="from_format",
                                            context=translator_config_copy,
                                            required=True,
                                            type_check=str)
            error_occured |= not ok

            to_format, ok = self._pop_key(source=translator_config,
                                          variable="to_format",
                                          context=translator_config_copy,
                                          required=True,
                                          type_check=str)
            error_occured |= not ok

            options, ok = self._pop_key(source=translator_config,
                                        variable="options",
                                        context=translator_config_copy,
                                        default=[],
                                        required=False,
                                        type_check=list)
            error_occured |= not ok

            input_after_option, ok = self._pop_key(source=translator_config,
                                                   variable="input_after_option",
                                                   context=translator_config_copy,
                                                   required=False,
                                                   type_check=str)
            error_occured |= not ok

            input_as_last_argument, ok = self._pop_key(source=translator_config,
                                                       variable="input_as_last_argument",
                                                       context=translator_config_copy,
                                                       required=False,
                                                       type_check=bool)
            error_occured |= not ok

            output_after_option, ok = self._pop_key(source=translator_config,
                                                    variable="output_after_option",
                                                    context=translator_config_copy,
                                                    required=False,
                                                    type_check=str)
            error_occured |= not ok

            executable, ok = self._pop_key(source=translator_config,
                                           variable="executable",
                                           context=translator_config_copy,
                                           required=True,
                                           type_check=str)
            error_occured |= not ok

            path, ok = self._pop_key(source=translator_config,
                                     variable="PATH",
                                     context=translator_config_copy,
                                     default=None,
                                     type_check=str)
            error_occured |= not ok

            if not error_occured:
                translator = Translator(from_format=from_format,
                                        to_format=to_format,
                                        executable=executable,
                                        options=options,
                                        input_as_last_argument=input_as_last_argument,
                                        input_after_option=input_after_option,
                                        output_after_option=output_after_option,
                                        PATH=path)
                try:
                    translator.verify()
                except FileNotFoundError:
                    self.log_error(f"executable not found: {translator.executable}", translator_config_copy)
                except BenchmarkException as e:
                    self.log_error(e, translator_config_copy)
                else:
                    TestInput.translators.append(translator)

            if translator_config:
                self.log_unknown_keys(translator_config, translator_config_copy)

    @Decorators.log_scope("testInputs")
    def _load_test_inputs(self, config: Dict):
        # test_inputs_config = config.pop("testInputs", None)
        test_inputs_config, ok = self._pop_key(source=config,
                                               variable="testInputs",
                                               context=config,
                                               required=True,
                                               type_check=list)
        if not ok:
            self._logger.error("You must define at least one testInput")
            return

        for test_input_config in test_inputs_config:
            # for error reporting
            test_input_config_copy = copy.deepcopy(test_input_config)

            error_occured = False
            name, ok = self._pop_key(source=test_input_config,
                                     variable="name",
                                     context=test_input_config_copy,
                                     required=True, type_check=str)
            error_occured |= not ok

            path, ok = self._pop_key(source=test_input_config,
                                     variable="path",
                                     context=test_input_config_copy,
                                     required=True,
                                     type_check=str)
            error_occured |= not ok

            format, ok = self._pop_key(source=test_input_config,
                                       variable="format",
                                       context=test_input_config_copy,
                                       required=True,
                                       type_check=str)
            error_occured |= not ok

            patterns, ok = self._pop_key(source=test_input_config,
                                         variable="files",
                                         context=test_input_config_copy,
                                         required=True,
                                         type_check=list)
            error_occured |= not ok

            files = []
            for pattern in patterns:
                wildcard = os.path.join(path, pattern)
                resolved_paths = glob.glob(wildcard, recursive=True)
                resolved_files = [resolved_path for resolved_path in resolved_paths if os.path.isfile(resolved_path)]
                if resolved_files:
                    files.extend(resolved_files)
                    self._logger.debug(f"{wildcard} matched files: {resolved_files}")
                else:
                    self.log_warning(f"pattern {wildcard} did not match any file")

            if not files:
                self.log_error(f"no file defined for testInput", test_input_config_copy)

            if not error_occured:
                test_input = TestInput(name=name,
                                       path=path,
                                       format=format,
                                       files=files)
                self.test_inputs.append(test_input)

            if test_input_config:
                self.log_unknown_keys(test_input_config, test_input_config_copy)

    @Decorators.log_scope("testSuites")
    def _load_test_suites(self, config: Dict):
        test_suites_config = config.pop("testSuites", None)
        if test_suites_config is None:
            self._logger.error("You must define at least one testSuite")
            return

        for test_suite_config in test_suites_config:
            # for error reporting
            test_suite_config_copy = copy.deepcopy(test_suite_config)

            error_occured = False
            name, ok = self._pop_key(source=test_suite_config,
                                     variable="name",
                                     context=test_suite_config_copy,
                                     required=True,
                                     type_check=str)
            error_occured |= not ok

            executable, ok = self._pop_key(source=test_suite_config,
                                           variable="executable",
                                           context=test_suite_config_copy,
                                           required=True,
                                           type_check=str)
            error_occured |= not ok

            PATH, ok = self._pop_key(source=test_suite_config,
                                     variable="PATH",
                                     context=test_suite_config_copy,
                                     required=False,
                                     type_check=str)
            error_occured |= not ok

            version_option, ok = self._pop_key(source=test_suite_config,
                                               variable="version_option",
                                               context=test_suite_config_copy,
                                               default="",
                                               required=False,
                                               type_check=str)
            error_occured |= not ok

            static_options, ok = self._pop_key(source=test_suite_config,
                                               variable="options",
                                               context=test_suite_config_copy,
                                               default=[],
                                               type_check=list,
                                               required=False)
            error_occured |= not ok

            test_cases = self._load_test_cases(test_suite_config)

            if not error_occured:
                test_suite = TestSuite(name=name,
                                       PATH=PATH,
                                       version_option=version_option,
                                       executable=executable,
                                       options=static_options,
                                       test_cases=test_cases)
                test_suite.verify()
                self.test_suites.append(test_suite)

            if test_suite_config:
                self.log_unknown_keys(test_suite_config, test_suite_config_copy)

    @Decorators.log_scope("testCases")
    def _load_test_cases(self, config: Dict):
        test_cases_config = config.pop("testCases", None)
        if test_cases_config is None:
            self._logger.error("You must define at least one testCase")
            return

        test_cases = []
        for test_case_config in test_cases_config:
            test_case_config_copy = copy.deepcopy(test_case_config)

            error_occured = False
            name, ok = self._pop_key(source=test_case_config,
                                     variable="name",
                                     context=test_case_config_copy,
                                     required=True,
                                     type_check=str)
            error_occured |= not ok

            input_as_stdin, ok = self._pop_key(source=test_case_config,
                                               variable="input_as_stdin",
                                               context=test_case_config_copy,
                                               required=False,
                                               type_check=bool)
            error_occured |= not ok

            input_as_last_arg, ok = self._pop_key(source=test_case_config,
                                                  variable="input_as_last_argument",
                                                  context=test_case_config_copy,
                                                  required=False,
                                                  type_check=bool)
            error_occured |= not ok

            input_after_option, ok = self._pop_key(source=test_case_config,
                                                   variable="input_after_option",
                                                   context=test_case_config_copy,
                                                   required=False,
                                                   type_check=str)
            error_occured |= not ok

            if not input_as_stdin and not input_as_last_arg and not input_after_option:
                self.log_error(f"input_as_stdin or input_as_last_arg or input_after_option must be defined",
                               test_case_config_copy)

            exclude, ok = self._pop_key(source=test_case_config,
                                        variable="exclude",
                                        context=test_case_config_copy,
                                        default=[],
                                        required=False,
                                        type_check=list)
            error_occured |= not ok

            if ok:
                for test_input_name in exclude:
                    if not any(test_input_name == test_input.name for test_input in self.test_inputs):
                        self.log_warning(f"exclude: there is no testInput called {test_input_name}",
                                         test_case_config_copy)

            include_only, ok = self._pop_key(source=test_case_config,
                                             variable="include_only",
                                             context=test_case_config_copy,
                                             default=[],
                                             required=False,
                                             type_check=list)
            error_occured |= not ok

            if exclude and include_only:
                self.log_error(f"exclude and include_only are mutually exclusive", test_case_config_copy)

            if ok:
                for test_input_name in include_only:
                    if not any(test_input_name == test_input.name for test_input in self.test_inputs):
                        self.log_warning(f"include_only: there is no testInput called {test_input_name}",
                                         test_case_config_copy)

            format, ok = self._pop_key(source=test_case_config,
                                       variable="format",
                                       context=test_case_config_copy,
                                       required=True,
                                       type_check=str)
            error_occured |= not ok

            # note: TestInput is assumed to be tptp
            # todo support chaining translators
            if ok:
                if not any(translator.to_format == format for translator in TestInput.translators):
                    self.log_warning(f"format {format} is not achievable with defined translators: ",
                                     TestInput.translators)

            # nested list
            options, ok = self._pop_key(source=test_case_config,
                                        variable="options",
                                        context=test_case_config_copy,
                                        required=True,
                                        type_check=list)
            error_occured |= not ok

            if not error_occured:
                test_case = TestCase(name=name,
                                     format=format,
                                     input_as_stdin=input_as_stdin,
                                     input_as_last_argument=input_as_last_arg,
                                     input_after_option=input_after_option,
                                     exclude=exclude,
                                     include_only=include_only,
                                     options=options)
                test_cases.append(test_case)

            if test_case_config:
                self.log_unknown_keys(test_case_config, test_case_config_copy)

        return test_cases

    def log_error(self, message, context=""):
        self._load_errors_occured = True
        if context:
            context = f"\ndetails:{context}"
        self._logger.error(f"In {'.'.join(self._log_scope)}: {message} {context}")

    def log_warning(self, message, context=""):
        if context:
            context = f"\ndetails:{context}"
        self._logger.warning(f"In {'.'.join(self._log_scope)}: {message} {context}")

    def log_missing_key(self, variable_name, contex):
        message = f"Missing required key: '{variable_name}'"
        self.log_error(message, contex)

    def log_unknown_keys(self, config, context=''):
        message = f"Unknown keys: '{config}'"
        self.log_warning(message, context=config)

    def _pop_key(self, source: Dict, variable: str, context: any, default: any = None, required: bool = False,
                 type_check: Type = None):
        """Remove and return variable from source and:
        add default value if not in source
        log error if required and not in source
        print context on error
        check type of variable
        """
        ok = True
        value = source.pop(variable, default)
        if required and value is None:
            ok = False
            self.log_missing_key(variable, context)

        if value is not None and type_check is not None and type(value) != type_check:
            ok = False
            self._logger.error(f"'{variable}'"
                               f" should be {type_check.__name__},"
                               f" but is {type(value).__name__}"
                               f" in {self.log_scope} {context}")
        return value, ok


if __name__ == "__main__":
    c = Config("../config.toml")
    c.load_config()
    pprint(c)
