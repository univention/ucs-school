#!/usr/bin/python3
#
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Central place to get logger for import."""

from __future__ import absolute_import

import logging
from typing import Optional  # noqa: F401

from ucsschool.lib.models.utils import UniFileHandler, UniStreamHandler, get_file_handler


def get_logger():  # type: () -> logging.Logger
    """
    Get a logging instance with name `ucsschool`.

    .. deprecated:: 4.4 v2
        Use `logging.getLogger(__name__)` and :py:func:`get_stream_handler()`,
        :py:func:`get_file_handler()`.

    :return: Logger
    :rtype: logging.Logger
    """
    logger = logging.getLogger("ucsschool.import")
    logger.warning('get_logger() is deprecated, use "logging.getLogger(__name__)" instead.')
    return logger


def make_stdout_verbose():  # type: () -> logging.Logger
    logger = logging.getLogger("ucsschool.import")
    for handler in logger.handlers:
        if isinstance(handler, UniStreamHandler):
            handler.setLevel(logging.DEBUG)
    return logger


def add_file_handler(filename, uid=None, gid=None, mode=None):
    # type: (str, Optional[int], Optional[int], Optional[int]) -> logging.Logger
    if filename.endswith(".log"):
        info_filename = "{}.info".format(filename[:-4])
    else:
        info_filename = "{}.info".format(filename)
    logger = logging.getLogger("ucsschool.import")
    if not any(isinstance(handler, UniFileHandler) for handler in logger.handlers):
        logger.addHandler(get_file_handler("DEBUG", filename, uid=uid, gid=gid, mode=mode))
        # TODO: bug to remove INFO file, or only create >=WARN/ERROR
        logger.addHandler(get_file_handler("INFO", info_filename, uid=uid, gid=gid, mode=mode))
    return logger


def move_our_handlers_to_lib_logger():  # type: () -> None
    """
    Move logging handlers from `ucsschool.import` to `ucsschool` logger.

    .. deprecated:: 4.4 v2
        Use `logging.getLogger(__name__)` and :py:func:`get_stream_handler()`,
        :py:func:`get_file_handler()` for the logger hierarchie required.
    """
    import_logger = logging.getLogger("ucsschool.import")
    import_logger.warning("move_our_handlers_to_lib_logger() is deprecated.")
    school_logger = logging.getLogger("ucsschool")
    for handler in import_logger.handlers:
        school_logger.addHandler(handler)
        import_logger.removeHandler(handler)
