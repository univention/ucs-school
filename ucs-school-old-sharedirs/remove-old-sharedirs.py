#
# Univention UCS@School
#  listener module
#
# Copyright 2007-2012 Univention GmbH
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
import univention.config_registry, commands, sys, os
import univention.debug

name='remove-old-sharedirs'
description='moves directories of removed group shares to backup folder'
filter='(objectClass=univentionShare)'
attributes=[]

target_dir_config = "ucsschool/listener/oldsharedir/targetdir"
source_dir_prefixes = "ucsschool/listener/oldsharedir/prefixes"

def check_target_dir(configRegistry):
	# either returns "" if everything is ok, or returns an error message

	if not configRegistry.has_key(target_dir_config):
		return "%s is not set" % target_dir_config

	target_dir=configRegistry[target_dir_config]

	if os.path.exists(target_dir) and not os.path.isdir(target_dir):
		return "%s is not a directory" % target_dir

	if not os.path.isdir(target_dir):
		# create directory
		listener.setuid(0)
		ret,ret_str = commands.getstatusoutput("mkdir -p '%s'" % target_dir)
		if not ret==0:
			return "failed to create target directory %s" % target_dir

	return ""

def check_source_dir(configRegistry, share_dir):
	# either returns "" if everything is ok, or returns an error message

	if not configRegistry.has_key(source_dir_prefixes):
		return "%s is not set" % source_dir_prefixes

	prefixlist=configRegistry[source_dir_prefixes].split(":")

	for prefix in prefixlist:
		if share_dir.startswith(prefix):
			return ""

	return "%s is not matched by %s" % (share_dir, source_dir_prefixes)

def handler(dn, new, old):

	configRegistry = univention.config_registry.ConfigRegistry()
	configRegistry.load()

	# remove empty share directories
	if old and not new:

		if old.has_key('univentionShareHost'):
			fqdn = '%s.%s' % (configRegistry['hostname'], configRegistry['domainname'])
			if not fqdn in old['univentionShareHost']:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Didn't do anything because this server is not in the share host list cn=%s" % (old["cn"][0]))
				return
		else:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing share directory of share %s: univentionShareHost ist not set" % (old["cn"][0]))
			return

		# check if target directory is okay

		ret=check_target_dir(configRegistry)
		if not ret=="":
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing share directory of share %s: %s" % (old["cn"][0], ret))
			return

		target_dir=configRegistry[target_dir_config]

		# check source (share) directory

		share_dir=""
		if not old.has_key("univentionSharePath"):
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing share directory of share %s: univentionSharePath is not set" % old["cn"][0])
			return
		else:
			share_dir=old["univentionSharePath"][0]

		ret=check_source_dir(configRegistry, share_dir)
		if not ret=="":
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing share directory of share %s: %s" % (old["cn"][0], ret))
			return

		if not os.path.isdir(share_dir):
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing share directory of share %s: it does not exist or is no directory" % old["cn"][0])
			return

		# make sure that we are dealing with a local filesystem
		ret, ret_str = commands.getstatusoutput("stat -f '%s' | grep 'Type:' | sed 's/.*Type:\ //'" % share_dir)

		if ret_str.strip() in ["nfs", "nfs4", "cifs", "smbfs", "nfsd"]:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "not removing share directory of share %s: is not on a local filesystem" % old["cn"][0])
			return


		ret=0
		ret_str=""
		try:
			try:
				listener.setuid(0)
				# for some reason, shutil cannot be imported, so we'll do it using mv
				ret, ret_str = commands.getstatusoutput("mv '%s' '%s'" % (share_dir, target_dir))
			except:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, "failed to move share directory of share %s from %s to %s: %s" % (old["cn"][0], share_dir, target_dir, sys.exc_info()[0]))
		finally:
			listener.unsetuid()
			if not ret==0:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, "failed to move share directory of share %s from %s to %s: %s" % (old["cn"][0], share_dir, target_dir, ret_str))

