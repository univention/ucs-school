#
# Univention UCS@school
#  listener module
#
# Copyright 2007-2016 Univention GmbH
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

__package__ = ''  # workaround for PEP 366
import listener
import os
import shutil
import time
from ldap import LDAPError
from psutil import disk_partitions
import univention.debug
from ucsschool.lib.models import School
from univention.admin.uldap import getMachineConnection


name = 'remove-old-homedirs'
description = 'moves directories of removed users away from home'
filter = '(objectClass=ucsschoolType)'
attributes = ["posixAccount"]
modrdn = '1'

DEFAUL_FS = "ext2/ext3:ext2:ext3:ext4:xfs:btrfs"
TARGET_BLACKLIST = ["/", "/boot", "/sys", "/proc", "/etc", "/dev"]

target_dir = listener.configRegistry.get("ucsschool/listener/oldhomedir/targetdir")
fs_types = listener.configRegistry.get("ucsschool/listener/oldhomedir/fs_types", DEFAUL_FS).split(":")
lo = None


def check_target_dir(dir):
	"""either returns "" if everything is ok, or returns an error message"""
	if not dir:
		return "targetdir is not set"

	# check target blacklist
	dir = dir.rstrip("/")
	if not dir or dir in TARGET_BLACKLIST:
		return "%s as target dir is invalid" % dir

	if os.path.exists(dir) and not os.path.isdir(dir):
		return "%s is not a directory" % dir

	# create directory
	if not os.path.isdir(dir):
		listener.setuid(0)
		try:
			os.makedirs(dir)
		except EnvironmentError as exc:
			return "failed to create target directory %s: %s" % (dir, exc)
		finally:
			listener.unsetuid()

	# check fs
	ret = check_filesystem(dir)
	if ret:
		return ret

	return ""


def check_source_dir(dir):
	"""either returns "" if everything is ok, or returns an error message"""
	if not os.path.exists(dir):
		return "%s does not exist" % dir
	if not os.path.isdir(dir):
		return "%s is not a directory" % dir

	# check fs
	ret = check_filesystem(dir)
	if ret:
		return ret

	return ""


def check_filesystem(dir):
	"""either returns "" if everything is ok, or returns an error message"""
	partitions = [(p[1], p[2]) for p in disk_partitions(True)]
	partitions.sort(key=lambda x: len(x[0]), reverse=True)
	path = os.path.realpath(os.path.abspath(dir))
	for k, v in partitions:
		if path.startswith(k):
			if v in fs_types:
				return ""
			else:
				break
	return "%s is not on a known filesystem" % dir


# move directory
def move_dir(src, dst, listener):
	"""either returns "" if everything is ok, or returns an error message"""
	newName = os.path.basename(src) + ".%s" % int(time.time())
	dst = os.path.join(dst, newName)
	ret = ""

	listener.setuid(0)
	try:
		shutil.move(src, dst)
	except EnvironmentError as exc:
		ret = str(exc)
	finally:
		listener.unsetuid()

	return ret


def warn(msg):
	univention.debug.debug(
		univention.debug.LISTENER,
		univention.debug.WARN,
		"remove-old-homedirs: {}".format(msg)
	)


def get_my_ous():
	"""find out which OUs this host is responsible for, returns list of strings"""
	return [s.name for s in School.get_all(lo)]


def prerun():
	global lo
	listener.setuid(0)
	try:
		lo, po = getMachineConnection(ldap_master=False)
	except LDAPError as exc:
		warn(str(exc))
		return
	finally:
		listener.unsetuid()


def postrun():
	global lo
	lo = None  # close LDAP connection


def handler(dn, new, old, command):
	my_ous = set(get_my_ous())
	users_ous = set(new.get("ucsschoolSchool", []))

	if (
		old and not new and not command == "r" or
		old and new and command == "m" and my_ous.isdisjoint(users_ous)
	):
		uid = old["uid"][0]

		home_dir = old.get("homeDirectory", [None])[0]
		if not home_dir:
			warn("not removing home of user %s: homeDirectory not set" % uid)
			return

		# check if target directory is okay
		ret = check_target_dir(target_dir)
		if ret:
			warn("not removing home of user %s: %s" % (uid, ret))
			return

		# check source (home) directory
		ret = check_source_dir(home_dir)
		if ret:
			warn("not removing home of user %s: %s" % (uid, ret))
			return

		# move it
		ret = move_dir(home_dir, target_dir, listener)
		if ret:
			warn("failed to move home of user %s from %s to %s: %s" % (uid, home_dir, target_dir, ret))
		return
