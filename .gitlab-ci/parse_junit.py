#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import pathlib
import sys
import xml.etree.ElementTree as ET  # nosec


def count_errors(junit_file):
    error_counter = 0
    tree = ET.parse(junit_file)  # noqa: S314
    root = tree.getroot()
    testsuites = root.findall("testsuite") if root.tag == "testsuites" else [root]

    for testsuite in testsuites:
        errors = int(testsuite.attrib.get("errors", "0"))
        failures = int(testsuite.attrib.get("failures", "0"))
        error_counter += errors + failures
    return error_counter


def clean_junit_xml(junit_file):
    """
    gitlab refuses to parse large junit files.
    This removes stdout and stderr from sucessful tests to decrease the file size.
    """
    tree = ET.parse(junit_file)  # noqa: S314
    root = tree.getroot()
    testsuites = root.findall("testsuite") if root.tag == "testsuites" else [root]

    for testsuite in testsuites:
        errors = int(testsuite.attrib.get("errors", "0"))
        failures = int(testsuite.attrib.get("failures", "0"))
        if errors == 0 and failures == 0:
            for testcase in testsuite.findall("testcase"):
                for tag in ["system-out", "system-err"]:
                    elem = testcase.find(tag)
                    if elem is not None:
                        testcase.remove(elem)

    tree.write(junit_file, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    test_report_path = pathlib.Path("./results")
    error_counter = 0
    for junit_file in test_report_path.glob("*/test-reports/**/*.xml"):
        print(f"Parsing {junit_file}")
        error_counter += count_errors(junit_file)
        clean_junit_xml(junit_file)
    if error_counter > 0:
        print(f"Found {error_counter} errors.")
        sys.exit(1)
