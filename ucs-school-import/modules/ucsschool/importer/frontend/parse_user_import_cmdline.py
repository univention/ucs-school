# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Default command line frontend for import.
"""
# Copyright 2016 Univention GmbH
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

from argparse import ArgumentParser


class ParseUserImportCmdline(object):
	"""
	Setup a command line frontend.
	"""
	def __init__(self):
		"""
		Setup the parser. Override to add more arguments or change the defaults.
		"""
		self.args = None
		# TODO: read defaults from user_import_defaults.json
		self.defaults = dict(
			dry_run=False,
			infile="/var/lib/ucs-school-import/new-format-userimport.csv",
			logfile=None,
			no_delete=False,
			school=None,
			sourceUID=None,
			user_role=None,
			verbose=False
		)
		self.parser = ArgumentParser(description="UCS@school import tool")
		self.parser.add_argument('-c', '--conffile', help="Configuration file to use (see "
			"/usr/share/doc/ucs-school-import for an explanation on configuration file stacking).")
		self.parser.add_argument('-i', '--infile', dest="infile", help="CSV file with users to import (shortcut for --set input:filename=...) [default: %(default)s].")
		self.parser.add_argument('-l', '--logfile',
			help="Write to additional logfile (shortcut for --set logfile=...).")
		self.parser.add_argument("--set", dest="settings", metavar="KEY=VALUE", nargs='*',
			help="Overwrite setting(s) from the configuration file. Use ':' in key to set nested values "
			"(e.g. 'scheme:email=...').")
		self.parser.add_argument("-m", "--no-delete", dest="no_delete", action="store_true",
			help="Only add/modify given user objects. User objects not mentioned within input files are not "
				"deleted/deactived (shortcut for --set no_delete=...) [default: %(default)s].")
		self.parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true",
			help="Dry run - don't actually commit changes to LDAP (shortcut for --set dry_run=...) "
				"[default: %(default)s].")
		self.parser.add_argument("--sourceUID", help="The ID of the source database (shortcut for --set sourceUID=...) "
			"[mandatory either here or in the configuration file].")
		self.parser.add_argument("-s", "--school", help="Name of school. Set only, if the source data does not contain "
			"the name of the school and all users are from one school (shortcut for --set school=...) "
			"[default: %(default)s].")
		self.parser.add_argument("-u", "--user_role", help="Set this, if the source data contains users with only one "
			"role <student|staff|teacher|teacher_and_staff> (shortcut for --set user_role=...) [default: %(default)s].")
		self.parser.add_argument("-v", "--verbose", action="store_true",
			help="Enable debugging output on the console [default: %(default)s].")
		self.parser.set_defaults(**self.defaults)

	def parse_cmdline(self):
		"""
		Parse the command line.

		:return: argparse.Namespace: the object with the parsed arguments
		assigned to attributes
		"""
		self.args = self.parser.parse_args()

		if (hasattr(self.args, "user_role") and
			self.args.user_role not in ["student", "staff", "teacher", "teacher_and_staff"]):
				self.parser.error("Invalid user role. Must be one of student, staff, teacher, teacher_and_staff.")

		settings = dict()
		if hasattr(self.args, "infile") and self.args.infile:
			settings["input"] = {"filename": self.args.infile}

		if hasattr(self.args, "settings") and self.args.settings:
			for setting in self.args.settings:
				try:
					k, v = setting.split("=")
				except ValueError:
					self.parser.error("Invalid setting '{}'.".format(setting))
				start, symb, end = k.rpartition(":")
				# try to convert to correct type
				if v.lower() == "true":
					v = True
				elif v.lower() == "false":
					v = False
				else:
					try:
						v = int(v)
					except ValueError:
						pass
				# support nested settings
				while symb:
					k = start
					v = {end: v}
					start, symb, end = start.rpartition(":")
				settings[k] = v
		self.args.settings = settings

		# only set shortcuts if they were set by the user
		for k, v in self.defaults.items():
			if getattr(self.args, k) != v:
				self.args.settings[k] = getattr(self.args, k)
		return self.args
