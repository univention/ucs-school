from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest
from faker import Faker

faker = Faker()


@pytest.fixture
def random_name() -> Callable[[], str]:
    return faker.first_name
