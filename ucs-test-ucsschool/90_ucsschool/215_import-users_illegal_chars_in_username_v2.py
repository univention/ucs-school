#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: remove illegal characters from username
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [42313, 42478]

import doctest

import ucsschool.importer.utils.username_handler

# prevent "InitialisationError: Configuration not yet loaded.":
from ucsschool.importer.utils.shell import config
from ucsschool.importer.utils.username_handler import MemoryStorageBackend, UsernameHandler

ucsschool.importer.utils.username_handler.noObject = KeyError
assert config


__module__ = __import__(__name__)

static_memory_storage_backend = MemoryStorageBackend("usernames")


class UsernameHandler(UsernameHandler):
    __doc__ = UsernameHandler.__doc__

    def __init__(self, max_length, dry_run=True):
        super(UsernameHandler, self).__init__(max_length, dry_run)
        self.storage_backend = static_memory_storage_backend


def test_import_users_illegal_chars_in_username_v2():
    result = doctest.testmod(__module__, verbose=True, raise_on_error=True)
    assert not result.failed and result.attempted, result
