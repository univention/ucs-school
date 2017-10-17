# Univention UCS@school
#
# Copyright 2007-2017 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import sqlite3
import os
import stat
import univention.config_registry


FN_NETLOGON_USER_QUEUE = '/var/spool/ucs-school-netlogon-user-logonscripts/user_queue.sqlite'


def get_netlogon_path_list():
	if not get_netlogon_path_list.script_path:
		ucr = univention.config_registry.ConfigRegistry()
		ucr.load()
		result = []
		ucsschool_netlogon_path = ucr.get('ucsschool/userlogon/netlogon/path', '').strip().rstrip('/')
		samba_netlogon_path = ucr.get('samba/share/netlogon/path', '').strip().rstrip('/')
		if ucsschool_netlogon_path:
			result.append(ucsschool_netlogon_path)
		elif samba_netlogon_path:
			result.append(samba_netlogon_path)
		else:
			result.append("/var/lib/samba/netlogon/user")
			result.append("/var/lib/samba/sysvol/%s/scripts/user" % (ucr.get('kerberos/realm', '').lower(),))
		get_netlogon_path_list.script_path = result
	return get_netlogon_path_list.script_path


get_netlogon_path_list.script_path = []


class SqliteQueueException(Exception):
	pass


class SqliteQueue(object):
	"""
	Holds items (user DNs) in a FIFO queue.
	"""
	IDX_DB_DN = 0

	def __init__(self, logger, filename=None):
		self.filename = filename if filename is not None else FN_NETLOGON_USER_QUEUE
		self.logger = logger
		self.db = None
		self.cursor = None
		self.setup_database()

	def setup_database(self):
		# close open db handle
		if self.db:
			try:
				self.db.close()
			except sqlite3.Error:
				pass
			self.cursor = None
			self.db = None

		# create directory if missing
		if not os.path.exists(os.path.dirname(self.filename)):
			self.logger.error('directory %r does not exist' % (os.path.dirname(self.filename),))
			raise SqliteQueueException('Cannot open database - directory %r does not exist' % (os.path.dirname(self.filename),))

		# open connection
		if not os.path.exists(self.filename):
			self.logger.warn('database does not exist - creating new one (filename=%r)' % (self.filename,))
		self.db = sqlite3.connect(self.filename)
		os.chown(self.filename, 0, 0)
		os.chmod(self.filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
		self.logger.debug('opened %r successfully' % (self.filename,))

		self.cursor = self.db.cursor()

		# create table if missing
		self.cursor.execute(u'CREATE TABLE IF NOT EXISTS user_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, userdn TEXT, username TEXT)')

		# save all changes to database
		self.db.commit()

	def truncate_database(self):
		# SQLITE does not have a TRUNCATE TABLE command, but DELETE FROM
		# without WHERE is optimized to delete the entire table without
		# iterating over its rows.
		self.cursor.execute(u'DELETE FROM user_queue')
		self.cursor.execute(u'VACUUM')
		self.db.commit()

	def commit(self):
		"""
		Commit outstanding changes to DB.
		"""
		self.db.commit()

	def add(self, userdn, username=None, db_commit=True):  # type: (str, Optional[bool]) -> None
		"""
		Adds a user DN to user queue if not already existant. If the user DN
		already exists in queue, the queue item remains unchanged.
		userdn and username have to be UTF-8 encoded strings or unicode strings.
		"""
		if isinstance(userdn, str):
			userdn = userdn.decode('utf-8')
		if isinstance(username, str):
			username = username.decode('utf-8')
		if username is not None:
			self.cursor.execute(u'insert or replace into user_queue (id, userdn, username) VALUES ((select id from user_queue where userdn = ?), ?, ?)', (userdn, userdn, username))
		else:
			self.cursor.execute(u'insert or replace into user_queue (id, userdn, username) VALUES ((select id from user_queue where userdn = ?), ?, (select username from user_queue where userdn = ?))', (userdn, userdn, userdn))
		if db_commit:
			self.db.commit()
		self.logger.debug('added/updated entry: userdn=%r  username=%s' % (userdn, username))

	def remove(self, userdn):  # type: (str) -> None
		"""
		Removes a specific user DN from queue.
		userdn has to be an UTF-8 encoded string or unicode string.
		"""
		if isinstance(userdn, str):
			userdn = userdn.decode('utf-8')
		self.cursor.execute(u'DELETE FROM user_queue WHERE userdn=?', (userdn,))
		self.db.commit()
		self.logger.debug('removed entry: userdn=%r' % (userdn,))

	def query_next_user(self):  # type: (None) -> [str]
		"""
		Returns next user dn and username of user_queue as UTF-8 encoded strings.
		"""
		query = u'SELECT userdn,username FROM user_queue ORDER BY id LIMIT 1'
		self.logger.debug('starting sqlite query: %r' % (query,))
		self.cursor.execute(query)
		row = self.cursor.fetchone()
		if row is not None:
			userdn = row[0]
			if userdn is not None:
				userdn = userdn.encode('utf-8')
			username = row[1]
			if username is not None:
				username = username.encode('utf-8')
			self.logger.debug('next entry: userdn=%r' % (userdn,))
			return (userdn, username)
		return (None, None)
