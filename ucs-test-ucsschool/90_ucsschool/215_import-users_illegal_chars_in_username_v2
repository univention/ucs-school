#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: remove illegal characters from username
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [42313, 42478]

import doctest
from ucsschool.importer.utils.username_handler import UsernameHandler, MemoryStorageBackend
import ucsschool.importer.utils.username_handler
ucsschool.importer.utils.username_handler.noObject = KeyError
from ucsschool.importer.utils.shell import config  # prevent "InitialisationError: Configuration not yet loaded."
assert config


static_memory_storage_backend = MemoryStorageBackend('usernames')


class UsernameHandler(UsernameHandler):
	__doc__ = UsernameHandler.__doc__

	def __init__(self, max_length, dry_run=True):
		super(UsernameHandler, self).__init__(max_length, dry_run)
		self.storage_backend = static_memory_storage_backend


if __name__ == '__main__':
	result = doctest.testmod()
	if result.failed or not result.attempted:
		raise ValueError(result)
