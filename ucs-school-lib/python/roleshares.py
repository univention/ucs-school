#!/usr/bin/python2.6
# -*- coding: iso-8859-15 -*-
#
# UCS@school lib
#  module: Role specific shares
#
# Copyright 2014 Univention GmbH
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

import os
import sys
import subprocess
import univention.config_registry
import univention.admin.uldap as udm_uldap
from ucsschool.lib.schoolldap import get_all_local_searchbases
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.lib.i18n import ucs_school_name_i18n

def localized_home_prefix(role, ucr):
	return ucr.get('ucsschool/import/roleshare/%s' % (role,), ucs_school_name_i18n(role))

def roleshare_home_prefix(school_ou, roles, ucr=None):
	if not ucr:
		ucr = univention.config_registry.ConfigRegistry()
		ucr.load()
		
	if ucr.is_true('ucsschool/import/roleshare', True):
		for role in (role_pupil, role_teacher, role_staff):
			if role in roles:
				return os.path.join(school_ou, localized_home_prefix(role, ucr))
	return ''

def create_roleshare(role, opts, ucr=None):
	if not ucr:
		ucr = univention.config_registry.ConfigRegistry()
		ucr.load()
		
	fqdn = "%(hostname)s.%(domainname)s" % ucr

	for searchbase in get_all_local_searchbases():
		school = searchbase.school
		position = searchbase.shares
		share = localized_home_prefix(role, ucr)
		directory = '/home/%s/%s' % (school, share,)
		teacher_groupname = "-".join((ucs_school_name_i18n(role_teacher), school))
		try:
			teacher_gid = grp.getgrnam(teacher_groupname).gr_gid
		except KeyError as ex:
			raise	## what else?

		cmd = ["univention-directory-manager", "shares/share", "create", "--ignore_exists"]
		if opts.binddn:
			cmd.extend(["--binddn", opts.binddn])
		if opts.bindpwd:
			cmd.extend(["--bindpwd", opts.bindpwd])

		cmd.extend(["--position", position])
		cmd.extend(["--set", "name=%s" % (share,)])
		cmd.extend(["--set", "path=%s" % (directory,)])
		cmd.extend(["--set", "host=%s" % (fqdn,)])
		cmd.extend(["--set", "group=%s" % (teacher_gid,)])
		cmd.extend(["--set", "sambaCustomSettings=admin user=@%s" % (teacher_groupname,)])

		p1 = subprocess.Popen([cmd], close_fds=True)
		p1.wait()
		if p1.returncode:
			sys.exit(p1.returncode)

if __name__ == '__main__':
	from optparse import OptionParser
	parser = OptionParser()
	parser.add_option("--setup", dest="setup",
		help="setup directories",
		action="store_true", default=False)
	parser.add_option("--binddn", dest="binddn",
		help="udm binddn")
	parser.add_option("--bindpwd", dest="bindpwd",
		help="udm bindpwd")
	(opts, args) = parser.parse_args()

	ucr = univention.config_registry.ConfigRegistry()
	ucr.load()
		
	if opts.setup:
		if ucr.is_true('ucsschool/import/roleshare', True):
			for role in (role_pupil, role_teacher, role_staff):
				create_roleshare(role, opts, ucr)
