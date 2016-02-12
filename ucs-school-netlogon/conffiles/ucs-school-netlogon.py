# -*- coding: utf-8 -*-
#
# UCS@school
#  config registry module for the netlogon script
#
# Copyright 2012-2016 Univention GmbH
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
import stat

logging = '>> %TEMP%\%USERNAME%-ucs-school-netlogon.log 2>&1'

def printHeader(fn):

	print >> fn, 'Set objShell = WScript.CreateObject("WScript.Shell")'
	print >> fn, 'Set objFSO = CreateObject("Scripting.FileSystemObject")'
	print >> fn
	print >> fn, 'temp = objShell.ExpandEnvironmentStrings("%TEMP%")'
	print >> fn, 'username = objShell.ExpandEnvironmentStrings("%USERNAME%")'
	print >> fn, 'logfile = objFSO.BuildPath(temp, username & "-ucs-school-netlogon.log")'
	print >> fn, 'baseName = objFSO.GetParentFolderName(Wscript.ScriptFullName)'
	print >> fn
	print >> fn, 'set fh = objFSO.CreateTextFile(logfile, True)'
	print >> fn, 'fh.Close'
	print >> fn
	print >> fn, 'sub printToLog(logfile, message)'
	print >> fn, '    set fh = objFSO.OpenTextFile(logfile, 8, True)'
	print >> fn, '    fh.WriteLine("")'
	print >> fn, '    fh.WriteLine(message)'
	print >> fn, '    fh.Close'
	print >> fn, 'end sub'
	print >> fn

def runCmd(script, fn, windowStyle, checkReturn):

	print >> fn, 'printToLog logfile, "running %s"' % script
	print >> fn, 'return = objShell.Run("%s %s", %s, true)' % (script, logging, windowStyle)

	if checkReturn:
		print >> fn, 'if return <> 0  then'
		print >> fn, '    MsgBox "%s failed with error code: " & return' % script
		print >> fn, 'end if'

	print >> fn
	print >> fn

def runVbs(script, fn, windowStyle, checkReturn, vbsInt, vbsOpts):

	print >> fn, 'printToLog logfile, "running %s"' % script
	print >> fn, 'script = objFSO.BuildPath(baseName, "%s")' % script
	print >> fn, 'return = objShell.run("%s %s " & script & " %s", %s, true)' % (vbsInt, vbsOpts, logging, windowStyle)
	
	if checkReturn:
		print >> fn, 'if return <> 0  then'
		print >> fn, '    MsgBox "%s failed with error code: " & return' % script
		print >> fn, 'end if'

	print >> fn
	print >> fn

def handler(configRegistry, changes):

	if not configRegistry.get("kerberos/realm"):
		return

	# samba3 samba4
	netlogonDirs = [
		"/var/lib/samba/netlogon",
		"/var/lib/samba/sysvol/%s/scripts" % configRegistry.get("kerberos/realm").lower()
	]

	# delete old ucsschool/import/set/netlogon/script/path
	old = changes.get("ucsschool/import/set/netlogon/script/path", "")
	if old and len(old) > 0 and old[0]:
		for netlogonDir in netlogonDirs:
			oldScript = os.path.join(netlogonDir, old[0])
			if os.path.isfile(oldScript):
				try:
					os.remove(oldScript)
				except:
					pass

	# netlogon script name
	netlogonScript = configRegistry.get("ucsschool/import/set/netlogon/script/path", "")
	if not netlogonScript:
		return

	# remove netlogon script
	for netlogonDir in netlogonDirs:
		netlogon = os.path.join(netlogonDir, netlogonScript)
		if os.path.isfile(netlogon):
			try:
				os.remove(netlogon)
			except:
				pass

	# get ucr vars and save script in scripts
	#   ucsschool/netlogon/<Paketname>/script=demo.cmd
	#   ucsschool/netlogon/<Paketname>/script/priority=10 - optional
	scripts = {}
	prefix = "ucsschool/netlogon/"
	for key in configRegistry.keys():
		if key and key.startswith(prefix):
			tmp = key.split("/")
			if len(tmp) > 3 and tmp[3] == "script":
				if len(tmp) > 4 and tmp[4] == "priority":
					continue
				script = configRegistry[key]
				priority = configRegistry.get(key + "/priority", sys.maxint)
				if not scripts.get(priority):
					scripts[priority] = []
				scripts[priority].append(script)

	# get config
	windowStyle = configRegistry.get("ucsschool/netlogon/windowStyle", "1")
	checkReturn = configRegistry.is_true("ucsschool/netlogon/checkReturn", True)
	vbsInt = configRegistry.get("ucsschool/netlogon/vbs/interpreter", "cscript")
	vbsOpts = configRegistry.get("ucsschool/netlogon/vbs/options", "")

	# nothing to write
	if not scripts:
		return

	# write logon script(s)
	for netlogonDir in netlogonDirs:
		if os.path.isdir(netlogonDir):
			filename = os.path.join(netlogonDir, netlogonScript)
			fn = open(filename, 'w')
			printHeader(fn)
			for key in sorted(scripts.keys(), key=int):
				for script in scripts[key]:
					if script.endswith(".cmd") or script.endswith(".bat"):
						runCmd(script, fn, windowStyle, checkReturn)
					elif script.endswith(".vbs"):
						runVbs(script, fn, windowStyle, checkReturn, vbsInt, vbsOpts)
					else:
						# hmm, do nothing
						pass
			fn.close()
			os.chmod(filename, (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH))
			os.chown(filename, 0, 0)
