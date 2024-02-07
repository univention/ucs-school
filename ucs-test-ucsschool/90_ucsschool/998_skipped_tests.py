#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Wrapper for currently skipped tests
## tags: [ucsschool_skipped_tests]
## roles: [domaincontroller_master]
## exposure: dangerous

import logging
import os
from subprocess import run
from typing import Any, Dict, Tuple

import pytest
import yaml

from univention.config_registry import ucr
from univention.testing.data import _TestReader


def get_current_version() -> str:
    return f"{ucr['version/version']}-0"


class SkippedTestWrapper:
    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger("SkippedTestLogger")
        self.logger.setLevel(logging.DEBUG)

        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s %(levelname)s:%(name)s: %(message)s"
        )

        fileHandler: logging.FileHandler = logging.FileHandler(
            "/var/log/univention/skipped_tests.log", mode="a", encoding=None, delay=False
        )
        fileHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)

        consoleHandler: logging.StreamHandler = logging.StreamHandler()
        consoleHandler.setFormatter(formatter)
        self.logger.addHandler(consoleHandler)

        assert os.environ.get(
            "PATH_TO_TEST_FILES"
        ), "Environment does not specify path to check for missed tests."
        self.logger.debug(
            f"Checking skipped tests in subdirectory of {os.environ.get('PATH_TO_TEST_FILES')} ."
        )

        assert os.environ.get(
            "FAIL_ON_MISSING_SOFTWARE"
        ), "Environment does not specify failure condition for missing software."
        self.logger.debug(
            f"Wrapper is set to fail on missing software: {os.environ.get('FAIL_ON_MISSING_SOFTWARE')} ."
        )

        assert os.environ.get(
            "MANUALLY_DISABLED_TESTS",
        ), "Environment does not specify tests to be automatically disabled."
        self.prevented_tests: list[str] = (
            os.environ.get("MANUALLY_DISABLED_TESTS").strip("][").split(", ")
        )

        self.current_version: str = get_current_version()
        self.skipped_tests: list[str] = self.get_skipped_tests(os.environ.get("PATH_TO_TEST_FILES"))

    def filter_files(self, filepath: str) -> Dict[str, Any]:
        # Consider only python test cases
        if not filepath.endswith(".py"):
            return None

        with open(filepath, "rb") as fp:
            try:
                shebang = fp.readline().decode("utf-8")
                possible_header_start = fp.tell()
                coding = fp.readline().decode("utf-8")
            except UnicodeEncodeError:
                self.logger.critical(
                    f"File {filepath} had unexpected encoding format (expected: UTF-8)."
                )
            if not shebang.startswith("#!"):
                self.logger.warning(f"File {filepath} does not include appropriate shebang.")
                return None

            if not coding.startswith("# -*- coding:"):
                coding = ""
                fp.seek(possible_header_start)

            header = {
                "shebang": shebang,
                "coding": coding,
            }

            # Parsing file header for filtering later on.
            # The 'yaml_data' dict is ordered accordingly to the
            # presence of data in the actual file.
            reader = _TestReader(fp)
            try:
                yaml_data = yaml.safe_load(reader)
            except yaml.scanner.ScannerError:
                self.logger.warning(f"No header data: Failed to read {filepath} .")
                return None
            try:
                for k, v in yaml_data.items():
                    header[k] = v
            except AttributeError:
                self.logger.warning(f"No header data: Could not retrieve header data of {filepath} .")
                return None

            if "tags" not in header.keys() or "versions" not in header.keys():
                return None
            return header

    def get_skipped_tests(self, base_path: str) -> Dict[str, Any]:
        skipped_tests: Dict[str, Any] = {}
        for path, subdirs, files in os.walk(base_path):
            for filename in files:
                filepath: str = os.path.join(path, filename)
                header: Dict[str, Any] = self.filter_files(filepath)
                if header is not None:
                    if "ucsschool" in header["tags"] and "fixed" not in header["versions"].values():
                        if "fixed" not in header["versions"].values():
                            header["versions"][self.current_version] = "fixed"
                            skipped_tests[filepath] = header
        return skipped_tests

    def get_file_content(self, path: str) -> str:
        # Parsing file excluding the already parsed header.
        content: str = "\n"

        with open(path) as fp:
            last_line_commented: bool = False
            for line in fp.readlines():
                if not line.startswith("#") and last_line_commented is False:
                    content += line
                last_line_commented = line.startswith("#")
        return content

    def get_header_string(self, header: Dict[str, Any]) -> str:
        # Reassembly of header from current testfile.
        content: str = ""
        content += header.pop("shebang")
        content += header.pop("coding")

        # keep versions keys as its not deconstructed properly
        versions = header.pop("versions", {})

        # parse header
        try:
            yaml_data = yaml.safe_dump(header).splitlines()
        except yaml.scanner.ScannerError:
            self.logger.warning("No header data: Corrupted header data while header reconstruction.")
            return None

        for i, line in enumerate(yaml_data):
            if line != "":
                content += f"## {line}"
            if i <= len(yaml_data) - 1:
                content += "\n"

        # add versions key to filecontent
        content += "## versions:\n"
        for version, tag in versions.items():
            content += f"##  {version}: {tag}\n"

        return content

    def create_fixed_tempfile(self, path: str, body_content: str, header: Dict[str, Any]) -> str:
        # Creating copy of a testfile with the 'fixed' version tag included.
        # i.e: /usr/share/ucs-test/90_ucsschool/777_dummy_test.py will be
        # copied as /usr/share/ucs-test/90_ucsschool/temp_777_dummy_test.py.
        separated_path: str = path.split("/")
        filename: str = f"temp_{separated_path[-1]}"
        base_path: str = "/".join(separated_path[0 : len(separated_path) - 1])
        temp_path: str = os.path.join(base_path, filename)
        header_content: str = self.get_header_string(header)

        with open(temp_path, "w") as fp:
            content = "".join([header_content, body_content])
            fp.write(content)

        return temp_path

    def run_single_test(self, path: str) -> Tuple[bool, str]:
        # Make test executable and run it.
        run(["chmod", "755", path], check=False)
        result = run([path, "-f"], check=False, capture_output=True, text=True)

        try:
            return True, result.stdout
        except Exception:
            return False, result.stderr


wrapper = SkippedTestWrapper()


@pytest.mark.parametrize("skipped_test", wrapper.skipped_tests.keys())
def test_run_skipped_test(skipped_test):
    fixed_test: str = None

    header = wrapper.skipped_tests[skipped_test]
    filecontent = wrapper.get_file_content(skipped_test)

    if skipped_test.rsplit("/", 1)[-1] not in wrapper.prevented_tests:
        fixed_test = wrapper.create_fixed_tempfile(skipped_test, filecontent, header)
        wrapper.logger.info(f"Skipped test {skipped_test} will be checked for unissued fix.")
    else:
        wrapper.logger.info(f"Skipped test {skipped_test} was manually disabled from checking.")
        return

    wrapper.logger.info(f"Running check on {fixed_test.replace('temp_','')}")
    result, content = wrapper.run_single_test(fixed_test)

    if result is True:
        wrapper.logger.info(f"Result of {skipped_test}")
        wrapper.logger.debug(content)
    elif result is False:
        wrapper.logger.warning(f"{skipped_test} failed to produce a result which can be evaluated!")

    os.remove(fixed_test)

    if result is True:
        if "Test passed" in content:
            wrapper.logger.error(f"{skipped_test} passed without 'fixed' version line.")
            wrapper.logger.error(content)
            assert False, content
        if (
            os.environ.get("FAIL_ON_MISSING_SOFTWARE") == "True"
            and "Test skipped (missing software)" in content
        ):
            wrapper.logger.error(f"Invalid result of {skipped_test} : Missing Software.")
            wrapper.logger.error(content)
            assert False, content
