# Univention UCS@School
#
# Copyright (C) 2007-2009 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

name='remove-old-homedirs'
description='moves directories of removed users away from home'
filter='(objectClass=posixAccount)'
attributes=[]

#import shutil
import listener
import re
import univention.config_registry, commands, sys, os
import univention.debug

target_dir_config = "ucsschool/listener/oldhomedir/targetdir"

def check_target_dir(configRegistry):
	# either returns "" if everything is ok, or returns an error message

	target_dir=configRegistry[target_dir_config]

	if not configRegistry.has_key(target_dir_config):
		return "%s is not set"%target_dir_config

	if os.path.exists(target_dir) and not os.path.isdir(target_dir):
		return "%s is not a directory"%target_dir

	if not os.path.isdir(target_dir):
		# create directory
		listener.setuid(0)
		ret,ret_str = commands.getstatusoutput("mkdir -p %s"%target_dir)
		if not ret==0:
			return "failed to create target directory %s"%target_dir

	return ""

def handler(dn, new, old):

	configRegistry = univention.config_registry.ConfigRegistry()
	configRegistry.load()

	# remove empty home directories
	if old and not new:

		# check if target directory is okay

		ret=check_target_dir(configRegistry)
		if not ret=="":
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing home directory of user %s: %s"%(old["uid"][0], ret))
			return

		target_dir=configRegistry[target_dir_config]

		# check source (home) directory

		home_dir=""
		if not old.has_key("homeDirectory"):
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing home directory of user %s, homeDirectory is not set"%old["uid"][0])
			return
		else:
			home_dir=old["homeDirectory"][0]

		if not os.path.isdir(home_dir):
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "not removing home directory of user %s, does not exist or is no directory"%old["uid"][0])
			return

		# make sure that we are dealing with a local filesystem
		ret, ret_str = commands.getstatusoutput('stat -f %s | grep "Type:" | sed "s/.*Type:\ //"'%home_dir)

		if ret_str in ["nfs", "nfs4", "cifs", "smbfs", "nfsd"]:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "not removing home directory of user %s, is not on a local filesystem"%old["uid"][0])
			return


		ret=0
		ret_str=""
		try:
			try:
				listener.setuid(0)
				# for some reason, shutil cannot be imported, so we'll do it using mv
				ret, ret_str = commands.getstatusoutput("mv %s %s"%(home_dir, target_dir))
			except:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, "failed to move home directory of user %s from %s to %s: %s"%(old["uid"][0], home_dir, target_dir, sys.exc_info()[0]))
		finally:
			listener.unsetuid()
			if not ret==0:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, "failed to move home directory of user %s from %s to %s: %s"%(old["uid"][0], home_dir, target_dir, ret_str))
