#
# Univention UCS@School
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

__package__=''  # workaround for PEP 366
import listener
import re
import commands
import sys
import os
import time
import shutil
import univention.debug

hostname=listener.baseConfig['hostname']
domainname=listener.baseConfig['domainname']
ip=listener.baseConfig['interfaces/eth0/address']
name='remove-old-sharedirs'
description='moves directories of removed group shares to backup folder'
filter='(&(objectClass=univentionShare)(|(univentionShareHost=%s.%s)(univentionShareHost=%s)))' % (hostname, domainname, ip)
attributes=[]
modrdn='1'

DEFAUL_FS="ext2/ext3:ext2:ext3:ext4:xfs:btrfs"
TARGET_BLACKLIST="/:/boot:/sys:/proc:/etc:/dev"

target_dir = listener.configRegistry.get("ucsschool/listener/oldsharedir/targetdir")
prefixlist = listener.configRegistry.get("ucsschool/listener/oldsharedir/prefixes", "").split(":")
fs_types = listener.configRegistry.get("ucsschool/listener/oldsharedir/fs_types", DEFAUL_FS).split(":")

# either returns "" if everything is ok, or returns an error message
def check_target_dir(dir):

	if not dir:
		return "targetdir is not set"

	# check target blacklist
	tmp = dir.rstrip("/")
	for i in TARGET_BLACKLIST.split(":"):
		if not tmp or tmp == i:
			return "%s as target dir is invalid" % dir

	if os.path.exists(dir) and not os.path.isdir(dir):
		return "%s is not a directory" % dir

	# create directory
	if not os.path.isdir(dir):
		listener.setuid(0)
		try:
			os.makedirs(dir)
		except:
			return "failed to create target directory %s" % dir
		finally:
			listener.unsetuid()

	# check fs
	ret = check_filesystem(dir)
	if ret:
		return ret

	return ""

# either returns "" if everything is ok, or returns an error message
def check_source_dir(prefixlist, dir):

	# check dir
	if not os.path.isdir(dir):
		return "%s is not a directory" % dir

	# check fs
	ret = check_filesystem(dir)
	if ret:
		return ret

	# check allowed prefix
	for prefix in prefixlist:
		if dir.startswith(prefix):
			return ""

	return "%s does not match any value in ucsschool/listener/oldsharedir/prefixes" % dir

# make sure that we are dealing with a known filesystem
def check_filesystem(dir):

	ret, out = commands.getstatusoutput("LC_ALL=C stat -f '%s'" % dir)
	myFs = ""
	for line in out.split("\n"):
		tmp = line.split("Type: ")
		if len(tmp) == 2:
			myFs = tmp[1].strip()
			for fs in fs_types:
				if fs.lower() == myFs.lower():
					# ok, 
					return ""
			break
	return "%s for %s is not on a known filesystem" % (myFs, dir)

# move directory
def move_dir(src, dst, listener):

	newName = os.path.basename(src) + ".%s" % int(time.time())
	dst = os.path.join(dst, newName)
	ret = ""

	listener.setuid(0)
	try:
		shutil.move(src, dst)
	except Exception, e:
		ret = str(e)
	finally:
		listener.unsetuid()

	return ret

def handler(dn, new, old, command):

	# remove empty share directories
	# if object is really removed (not renamed)
	if old and not new and not command == "r":

		name = old["cn"][0]

		# check object
		if not old.get("univentionShareHost") or not old.get("univentionSharePath"):
			univention.debug.debug(
				univention.debug.LISTENER, univention.debug.WARN,
				"not removing directory of share %s: univentionShareHost(Path) ist not set" % name)
			return

		share_dir = old["univentionSharePath"][0]

		# check if target directory is okay
		ret = check_target_dir(target_dir)
		if ret:
			univention.debug.debug(
				univention.debug.LISTENER, univention.debug.WARN,
				"not removing directory of share %s: %s" % (name, ret))
			return

		# check source (share) directory
		ret = check_source_dir(prefixlist, share_dir)
		if ret:
			univention.debug.debug(
				univention.debug.LISTENER, univention.debug.WARN, 
				"not removing share directory of share %s: %s" % (name, ret))
			return

		# move it
		ret = move_dir(share_dir, target_dir, listener)
		if ret:
			univention.debug.debug(
				univention.debug.LISTENER, univention.debug.ERROR,
				"failed to move directory of share %s from %s to %s: %s" % (name, share_dir, target_dir, ret))
