import packaging.version
import ucsschool.kelvin.constants


def test_parse_version():
    packaging.version.parse(ucsschool.kelvin.constants.__version__)
