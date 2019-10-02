import logging
import ucsschool.kelvin.utils


def test_get_logger():
    logger = ucsschool.kelvin.utils.get_logger(__name__)
    assert logger.level == logging.DEBUG
    assert "kelvin-api" in (handler.name for handler in logger.handlers)


def test_get_logger_no_double_handlers():
    logger = ucsschool.kelvin.utils.get_logger(__name__)
    num1 = len(logger.handlers)
    logger = ucsschool.kelvin.utils.get_logger(__name__)
    assert len(logger.handlers) == num1
