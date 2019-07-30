#!/usr/share/ucs-test/runner /usr/bin/pytest -l -s -v
## -*- coding: utf-8 -*-
## desc: test get_file_handler function
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: safe
## packages:
##   - python-ucs-school

import os
import logging
import tempfile
from logging import CRITICAL, ERROR, WARN, WARNING, INFO, DEBUG, NOTSET
import pytest
import univention.testing.strings as uts
from ucsschool.lib.models.utils import get_file_handler


@pytest.fixture
def random_logger():
	def _func():
		handler = get_file_handler("DEBUG", tempfile.mkstemp()[1])
		logger = logging.getLogger(uts.random_username())
		logger.addHandler(handler)
		logger.setLevel("DEBUG")
		return logger
	return _func


@pytest.mark.parametrize("level", (
		('CRITICAL', CRITICAL),
		('ERROR', ERROR),
		('WARN', WARNING),
		('WARNING', WARNING),
		('INFO', INFO),
		('DEBUG', DEBUG),
		('NOTSET', NOTSET)))
def test_get_file_handler_translates_string_loglevels(level):
	level_name, level_value = level
	fd, file_name = tempfile.mkstemp()
	assert get_file_handler(level_name, file_name).level == level_value
	os.remove(file_name)


def test_password_not_in_arg_is_logged(random_logger):
	logger = random_logger()
	random_string = uts.random_string(20)
	logger.debug(random_string)
	password_string = "password s3cr3t"
	logger.debug(password_string)
	random_arg = {"foo": uts.random_string()}
	logger.debug("random_arg: %r", random_arg)
	logger.handlers[-1].flush()
	with open(logger.handlers[-1].baseFilename, "r") as fp:
		txt = fp.read()
	assert random_string in txt
	assert password_string in txt
	assert "random_arg: {!r}".format(random_arg) in txt


def test_password_in_single_arg_is_not_logged(random_logger):
	logger = random_logger()
	random_dict = dict([(uts.random_string(), uts.random_string())])
	logger.debug("a dict: %r", random_dict)
	password_string = uts.random_string(20)
	dict_with_pw = {"bar": uts.random_string(), "password": password_string}
	logger.debug("dict with pw: %r", dict_with_pw)
	logger.handlers[-1].flush()
	with open(logger.handlers[-1].baseFilename, "r") as fp:
		txt = fp.read()
	assert "a dict: {!r}".format(random_dict) in txt
	assert password_string not in txt
	assert "dict with pw: " in txt
	assert "bar" in txt
	assert "password" in txt
	assert dict_with_pw["bar"] in txt


def test_password_in_multiple_args_is_not_logged(random_logger):
	logger = random_logger()
	random_dict1 = dict([(uts.random_string(), uts.random_string())])
	logger.debug("a dict: %r", random_dict1)
	password_string = uts.random_string(20)
	random_dict2 = dict([(uts.random_string(), uts.random_string())])
	random_dict3 = dict([(uts.random_string(), uts.random_string())])
	dict_with_pw = {"bar": uts.random_string(), "password": password_string}
	logger.debug("dict no pw: %r dict with pw: %r dict no pw: %r", random_dict2, dict_with_pw, random_dict3)
	logger.handlers[-1].flush()
	with open(logger.handlers[-1].baseFilename, "r") as fp:
		txt = fp.read()
	assert "a dict: {!r}".format(random_dict1) in txt
	assert password_string not in txt
	assert "dict with pw: " in txt
	assert "dict no pw: " in txt
	assert "bar" in txt
	assert "password" in txt
	assert dict_with_pw["bar"] in txt
	assert random_dict2.keys()[0] in txt
	assert random_dict3.keys()[0] in txt
	assert random_dict2.values()[0] in txt
	assert random_dict3.values()[0] in txt
