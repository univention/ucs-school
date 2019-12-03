import logging

from ucsschool.lib.models.utils import get_file_handler

from .constants import LOG_FILE_PATH


def setup_logging() -> None:
    for name in (
        None,
        "requests",
        "univention",
        "ucsschool",
        "uvicorn.access",
        "uvicorn.error",
    ):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
    file_handler = get_file_handler(logging.DEBUG, str(LOG_FILE_PATH))
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger = logging.getLogger("uvicorn.access")
    logger.addHandler(file_handler)
