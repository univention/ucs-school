import csv
import pytest

try:
    from typing import Dict, Generator
except ImportError:
    pass


@pytest.fixture(scope="session")
def rows():
    def _func(csv_file_name):  # type: (str) -> Generator[Dict[str, str]]
        with open(csv_file_name) as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                yield row

    return _func


@pytest.fixture(scope="session")
def get_one_row(rows):
    def _func(csv_file, column_name, column_value):  # type: (str, str, str) -> Dict[str, str]
        for row in rows(csv_file):
            if row[column_name] == column_value:
                return row
        raise ValueError("No row found that had a column {!r} with value {!r}.".format(column_name, column_value))

    return _func


@pytest.fixture(scope="session")
def check_failure_count(rows):
    def _func(csv_file):  # type: (str) -> None
        for row in rows(csv_file):
            print("row={!r}".format(row))
            col = "Failure Count"
            value = int(row[col])
            assert value == 0

    return _func


@pytest.fixture(scope="session")
def check_rps(get_one_row):
    def _func(csv_file, url_name, expected_min):  # type: (str, str, float) -> None
        row = get_one_row(csv_file, "Name", url_name)
        col = "Requests/s"
        value = float(row[col])
        assert value > expected_min

    return _func


@pytest.fixture(scope="session")
def check_95_percentile(get_one_row):
    def _func(csv_file, url_name, expected_max):  # type: (str, str, int) -> None
        row = get_one_row(csv_file, "Name", url_name)
        col = "95%"
        value = int(row[col])
        assert value < expected_max

    return _func
