import logging

from ucsschool.lib.models.utils import get_file_handler, get_stream_handler

from .constants import LOG_FILE_PATH


def enable_ucsschool_lib_debugging():
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("univention").setLevel(logging.DEBUG)
    logger = logging.getLogger("ucsschool")
    logger.setLevel(logging.DEBUG)
    if "ucsschool" not in [h.name for h in logger.handlers]:
        handler = get_stream_handler(logging.DEBUG)
        handler.set_name("ucsschool")
        logger.addHandler(handler)


enable_ucsschool_lib_debugging()
_logger = logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """
    Create logger with name `name` and attach file and stream handlers.
    Call from your module like this `get_logger(__name__)`.

    :param str name: name of logger
    :return: logger instance with handlers attached
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)
    if "kelvin-api" not in [h.name for h in logger.handlers]:
        logger.setLevel(logging.DEBUG)
        handler = get_stream_handler(logging.DEBUG)
        handler.set_name("kelvin-api")
        logger.addHandler(handler)
        handler = get_file_handler(logging.DEBUG, LOG_FILE_PATH)
        handler.set_name("kelvin-api")
        logger.addHandler(handler)
    return logger
