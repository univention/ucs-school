#!/usr/share/ucs-test/runner pytest-3
## -*- coding: utf-8 -*-
## desc: Import users via CLI - check for validation errors
## tags: [apptest,ucsschool,ucsschool_import2]
## roles: [domaincontroller_master]
## exposure: dangerous
## timeout: 36000
## packages:
##   - ucs-school-import

import csv
import re
import subprocess
from typing import List

from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester

users = [
    Person("DEMOSCHOOL", "teacher"),
    Person("DEMOSCHOOL", "student"),
    Person("DEMOSCHOOL", "student"),
]

mapping = {
    "OUs": "schools",
    "Vor": "firstname",
    "Nach": "lastname",
    "Gruppen": "school_classes",
    "E-Mail": "email",
    "Beschreibung": "description",
    "Typ": "__role",
}

config_values = {"tolerate_errors": 2, "csv": {"mapping": mapping}, "user_role": None}

tester = CLI_Import_v2_Tester()
config_json = tester.create_config_json(values=config_values)

import_cmd = ["/usr/share/ucs-school-import/scripts/ucs-school-user-import", "-c", config_json]


def create_import_csv(err: bool) -> str:
    csv_fn = tester.create_csv_file(person_list=users, mapping=mapping)

    tmp = []

    with open(csv_fn, newline="") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=",", quotechar='"')

        tmp.append(reader.fieldnames)

        for row in reader:
            if err and row["Typ"] == "teacher":
                row["Typ"] = "triggererror"
            elif not err and row["Typ"] == "teacher":
                row["Typ"] = "student"
            tmp.append(row)

    with open(csv_fn, newline="", mode="w") as csv_f:
        writer = csv.DictWriter(
            csv_f, fieldnames=tmp[0], restval="", delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        writer.writerows(tmp[1:])

    return csv_fn


def run_import(args: List[str], valid: bool = True):
    cmd = import_cmd + args

    proc = subprocess.run(cmd, capture_output=True, text=True)  # noqa: PLW1510

    print("\nOUT:\n", proc.stdout, "\n")
    print("\nERROR:\n", proc.stderr, "\n")

    num_users = re.search(
        "------ User import statistics ------.*Read users from input data: ([0-9]*)",
        proc.stderr,
        flags=re.DOTALL,
    )
    num_created = re.search(
        "------ User import statistics ------.*Created ImportStudent: ([0-9]*)",
        proc.stderr,
        flags=re.DOTALL,
    )
    num_modified = re.search(
        "------ User import statistics ------.*Modified ImportStudent: ([0-9]*)",
        proc.stderr,
        flags=re.DOTALL,
    )
    num_err = re.search(
        "------ User import statistics ------.*Errors: ([0-9]*)", proc.stderr, flags=re.DOTALL
    )

    validation_errors = re.findall("ucsschool.lib.models.attributes.ValidationError: {}", proc.stderr)

    assert len(validation_errors) == 0

    assert num_users is not None
    assert num_created is not None
    assert num_modified is not None
    assert num_err is not None

    num_users = int(num_users[1])
    num_created = int(num_created[1])
    num_modified = int(num_modified[1])
    num_err = int(num_err[1])

    if valid:
        assert num_users == 3
        assert num_created + num_modified == 3
        assert num_err == 0
    else:
        assert num_users == 2
        assert num_created + num_modified == 2
        assert num_err == 1


def test_import_dryrun():
    args = ["-i", create_import_csv(err=False), "-n"]

    run_import(args)


def test_import_dryrun_with_invalid_role():
    args = ["-i", create_import_csv(err=True), "-n"]

    run_import(args, valid=False)


def test_import():
    args = ["-i", create_import_csv(err=False)]

    run_import(args)


def test_import_with_invalid_role():
    args = ["-i", create_import_csv(err=True)]

    run_import(args, valid=False)
