import packaging.version

import ucsschool.kelvin


def test_parse_version():
    packaging.version.parse(ucsschool.kelvin.__version__)
