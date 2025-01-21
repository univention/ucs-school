#!/usr/bin/env python3
import pathlib
import sys
import xml.etree.ElementTree as ET  # nosec


def count_errors(test_suite):
    return int(test_suite.attrib["failures"]) + int(test_suite.attrib["errors"])


if __name__ == "__main__":
    test_report_path = pathlib.Path("./results")
    error_counter = 0
    for junit_file in test_report_path.glob("*/test-reports/**/*.xml"):
        print(f"Parsing {junit_file}")
        root = ET.fromstring(junit_file.open().read())  # noqa: S314
        if root.tag == "testsuites":
            for test_suite in root:
                error_counter += count_errors(test_suite)
        elif root.tag == "testsuite":
            error_counter = count_errors(root)
        else:
            print("Parse error.", file=sys.stderr)
            sys.exit(1)
        if error_counter > 0:
            print(f"Found {error_counter} errors.")
            sys.exit(1)
