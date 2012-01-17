# -*- coding: utf-8 -*-
#
# UCS@school
#  config registry module for the netlogon script
#
# Copyright 2012 Univention GmbH
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

import univention.uldap
import sys
import os

def printHeader(fn, netlogon):

	if not fn:
		fn = open(netlogon, 'w')
		print >> fn, 'Set objShell = WScript.CreateObject("WScript.Shell")'
		print >> fn, 'Set objFSO = CreateObject("Scripting.FileSystemObject")'
		print >> fn, 'baseName = objFSO.GetParentFolderName(Wscript.ScriptFullName)'
		print >> fn

	return fn


def runCmd(script, fn, windowStyle, checkReturn):

	print >> fn, 'return = objShell.Run("%s", %s, true)' % (script, windowStyle)

	if checkReturn:
		print >> fn, 'if return <> 0  then'
		print >> fn, '    MsgBox "run.cmd failed with error code: " & return'
		print >> fn, 'end if'

	print >> fn
	print >> fn

def runVbs(script, fn, windowStyle, checkReturn):

	print >> fn, 'script = objFSO.BuildPath(baseName, "%s")' % script
	print >> fn, 'return = objShell.run("wscript " & script, %s, true)' % windowStyle
	
	if checkReturn:
		print >> fn, 'if return <> 0  then'
		print >> fn, '    MsgBox "run.cmd failed with error code: " & return'
		print >> fn, 'end if'

	print >> fn
	print >> fn

def handler(configRegistry, changes):

	# check samba3 samba4
	netlogonDir = "/var/lib/samba/netlogon"
	lo = univention.uldap.getMachineConnection(ldap_master = False)
	result = lo.search('(&(cn=%s)(univentionService=Samba 4))' % configRegistry.get("hostname", "localhost"))
	if result:
		netlogonDir = "/var/lib/samba/sysvol/%s/scripts" % configRegistry.get('kerberos/realm', '').lower()
	if not os.path.isdir(netlogonDir):
		print >> sys.stderr, "error: %s is not a valid directory" % netlogonDir
		sys.exit(1)

	# delete old ucsschool/import/set/netlogon/script/path
	old = changes.get("ucsschool/import/set/netlogon/script/path", "")
	if len(old) > 0 and old[0]:
		old = os.path.join(netlogonDir, old[0])
		if os.path.isfile(old):
			os.remove(old)

	# netlogon script name
	netlogonScript = configRegistry.get("ucsschool/import/set/netlogon/script/path", "")
	if not netlogonScript:
		sys.exit(0)
	netlogon = os.path.join(netlogonDir, netlogonScript)

	# get ucr vars and save script in scripts
	scripts = {}
	prefix = "ucsschool/netlogon/script/"
	for key in configRegistry.keys():
		if key and key.startswith(prefix):
			script = configRegistry[key]
			number = key.replace(prefix, "")
			scripts[number] = script
	windowStyle = configRegistry.get("ucsschool/netlogon/windowStyle", "1")
	checkReturn = configRegistry.is_true("ucsschool/netlogon/checkReturn", True)

	fn = False
	for key in sorted(scripts.keys()):
		script = scripts[key]

		if script.endswith(".cmd") or script.endswith(".bat"):
			fn = printHeader(fn, netlogon)
			runCmd(script, fn, windowStyle, checkReturn)
		elif script.endswith(".vbs"):
			fn = printHeader(fn, netlogon)
			runVbs(script, fn, windowStyle, checkReturn)
		else:
			# hmm, do nothing 
			pass	
