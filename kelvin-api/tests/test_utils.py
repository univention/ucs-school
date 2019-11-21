import logging

import ucsschool.kelvin.utils


def test_get_logger(random_name):
    name = random_name()
    logger = ucsschool.kelvin.utils.get_logger(name)
    assert logger.name == name
    assert logger.level == logging.DEBUG
    assert "kelvin-api" in (handler.name for handler in logger.handlers)


def test_get_logger_no_double_handlers(random_name):
    name = random_name()
    logger = ucsschool.kelvin.utils.get_logger(name)
    num1 = len(logger.handlers)
    logger = ucsschool.kelvin.utils.get_logger(name)
    assert len(logger.handlers) == num1
