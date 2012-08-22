# Univention UCS@School
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
import univention.config_registry
import univention.debug
import univention.utf8

import os, pwd, types, ldap, ldap.schema, re, time, copy, codecs, base64

hostname=listener.baseConfig['hostname']
domainname=listener.baseConfig['domainname']
ip=listener.baseConfig['interfaces/eth0/address']

name='ucs-school-user-logonscript'
description='Create user-specific netlogon-scripts'
filter='(|(&(objectClass=posixAccount)(objectClass=organizationalPerson)(!(uid=*$)))(objectClass=posixGroup)(objectClass=univentionShare))'
atributes=[]

scriptpath = []
desktopFolderName = "Eigene Shares"
globalLinks = {}

# create netlogon scripts for samba3 and samba4
def getScriptPath():

	global scriptpath

	if scriptpath:
		return

	scriptpath.append("/var/lib/samba/netlogon/user")
	scriptpath.append("/var/lib/samba/sysvol/%s/scripts/user" % listener.configRegistry.get('kerberos/realm', '').lower())

	for path in scriptpath:
			listener.setuid(0)
			try:
				if not os.path.isdir(path):
					os.makedirs(path)
			finally:
				listener.unsetuid()

def getCommandOutput(command):
	child = os.popen(command)
	data = child.read()
	err = child.close()
	if err:
		raise RuntimeError, '%s failed with exit code %d' % (command, err)
	return data

def connect():

	connection = False
	listener.setuid(0)
	try:
		connection = univention.uldap.getMachineConnection(ldap_master = False)
	finally:
			listener.unsetuid()

	return connection


def getGlobalLinks():
	# search in baseconfig for shares which are common for all users
	share_keys = []
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: search for global links")
	if listener.baseConfig.has_key('ucsschool/userlogon/commonshares') and listener.baseConfig['ucsschool/userlogon/commonshares']:
		l = getConnection()
		ldapbase = listener.baseConfig['ldap/base']
		share_keys = listener.baseConfig['ucsschool/userlogon/commonshares'].split(',')
		for key in share_keys:
			# check if share exists
			res_shares = []
			try:
				res_shares = l.search(scope="sub", filter='(&(objectClass=univentionShareSamba)(|(cn=%s)(univentionShareSambaName=%s)))' % (key,key), attr=['cn'])
			except:
				pass
			if len(res_shares) > 0:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: search global links for %s" % key)
				if listener.baseConfig.has_key('ucsschool/userlogon/commonshares/server/%s' % key):
					server = listener.baseConfig['ucsschool/userlogon/commonshares/server/%s' % key]
					if listener.baseConfig.has_key('ucsschool/userlogon/commonshares/letter/%s' % key):
						letter = listener.baseConfig['ucsschool/userlogon/commonshares/letter/%s' % key].replace(':','')
						globalLinks[key] = {'server':server,'letter':letter}
					else:
						globalLinks[key] = {'server':server}
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: got global links %s" % globalLinks)


def generateMacScript(uid, name, host):
	return '''#!/bin/sh # generated script for accessing a samba share
/usr/bin/osascript <<EOF
tell application "Finder"
 open location "smb://%s@%s/%s"
 activate
end tell
EOF
''' % (uid, host, name)

def writeMacLinkScripts(uid, homepath, links):
	listener.setuid(0)
	try:
		if not (os.path.exists(homepath) and not os.path.isdir(homepath)): # may be /dev/null
			# check existance of home
			uidnumber = 0
			gidnumber = 0
			try:
				uidnumber = pwd.getpwnam(uid)[2]
				gidnumber = pwd.getpwnam(uid)[3]
			except:
				pass

			if not os.path.exists(os.path.join(homepath, "Desktop", desktopFolderName)):
				if not os.path.exists(homepath):
					os.mkdir(homepath, 0700)
					os.chown(homepath, uidnumber, gidnumber)

				for path in [os.path.join(homepath, "Desktop"), os.path.join(homepath, "Desktop", desktopFolderName)]:
					if not os.path.exists(path):
						os.mkdir(path)
						os.chown(path, uidnumber, gidnumber)

			# remove old scripts
			for file in os.listdir(os.path.join(homepath, "Desktop", desktopFolderName)):
				try:
					os.remove(os.path.join(homepath, "Desktop", desktopFolderName,file))
				except:
					univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, "ucsschool-user-logonscripts: failed to remove %s" % file)
					raise

			for name in links:
				macscriptpath = os.path.join(homepath, "Desktop", desktopFolderName, "%s.app" % name)
				fp = open(macscriptpath ,'w')
				fp.write(generateMacScript(uid, name, links[name]).replace('\n','\r\n'))
				fp.close()
				os.chmod(macscriptpath, 0500)
				os.chown(macscriptpath, uidnumber, gidnumber)
	finally:
			listener.unsetuid()

def generateWindowsLinkScript(desktopfolder, links, mappings):
	# desktopfolder is a strings, links is a list of tupels which contain linkname and linkgoal
	skript = '''Const DESKTOP = &H10&
Const FolderName = "%s"
Const HKEY_CURRENT_USER= &H80000001

Set objShell = CreateObject("Shell.Application")
Set objFolder = objShell.Namespace(DESKTOP)
Set objFolderItem = objFolder.Self
Set FileSysObj = WScript.CreateObject("Scripting.FileSystemObject")
Set WSHNetwork = WScript.CreateObject("WScript.Network")

FolderPath = objFolderItem.Path + "\\" + FolderName

\' Delete Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
If objFSO.FolderExists(FolderPath) Then
	objFSO.DeleteFolder(FolderPath)
End If

\' Recreate Folder
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objFolder = objFSO.CreateFolder(FolderPath)

\' Link to HOMEDRIVE
Set oShell = CreateObject("Wscript.Shell")
homepath = oShell.Environment("Process").Item("HOMEDRIVE") & oShell.Environment("Process").Item("HOMEPATH")

Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = FolderPath + "\\Meine Dateien.LNK"

Set oLink = oWS.CreateShortcut(sLinkFile)

oLink.TargetPath = homepath
oLink.Save

Function SetMyShares(strPersonal)
 strKeyPath1="Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
 strKeyPath2="Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"

 strComputer = GetComputerName
 Set objReg = GetObject("winmgmts:{impersonationLevel=impersonate}!" & strComputer & "\\root\\default:StdRegProv")

 \' Check if folder Eigene Dateien exists
 Set fso = CreateObject("Scripting.FileSystemObject")
 If not (fso.FolderExists(strPersonal)) then
	 ON ERROR RESUME NEXT
	 Set f = fso.CreateFolder(strPersonal)
 End If

 intRet1= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath1, "Personal", strPersonal)
 If intRet1 <> 0 Then
    Wscript.echo "Error: Setting Shell Folder Key Personal"
 End If

 intRet2= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath2, "Personal", strPersonal)
 If intRet2 <> 0 Then
     Wscript.echo "Error: Setting User Shell Folder Key Personal"
 End If

 \' Check if folder Eigene Bilder exists
 Set fso = CreateObject("Scripting.FileSystemObject")
 If not (fso.FolderExists(strPersonal & "\Eigene Bilder")) then
	 ON ERROR RESUME NEXT
	 Set f = fso.CreateFolder(strPersonal & "\Eigene Bilder")
 End If

 intRet3= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath1, "My Pictures", strPersonal & "\Eigene Bilder")
 If intRet3 <> 0 Then
	Wscript.echo "Error: Setting Shell Folder Key Personal"
 End If

 intRet4= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath2, "My Pictures", strPersonal & "\Eigene Bilder")
 If intRet4 <> 0 Then
	 Wscript.echo "Error: Setting User Shell Folder Key Personal"
 End If

 end function

Function MapDrive(Drive,Share)
 ON ERROR RESUME NEXT
 If FileSysObj.DriveExists(share)=True then
 if FileSysObj.DriveExists(Drive)=True then
 WSHNetwork.RemoveNetworkDrive Drive
 end if
 end if
 WSHNetwork.MapNetworkDrive Drive, Share
 If err.number >0 then
 msgbox "ERROR: " & err.description & vbcr & Drive & " " & share
 err.clear
 End if
 end function

''' % desktopfolder

	# create shortcuts to shares
	for linkName in links:
		skript += 'Set oWS = WScript.CreateObject("WScript.Shell")\n'
		skript += 'sLinkFile = FolderPath + "\\%s.LNK"\n' % linkName
		skript += 'Set oLink = oWS.CreateShortcut(sLinkFile)\n'
		skript += 'oLink.TargetPath = "\\\\%s\\%s"\n' % (links[linkName], linkName)
		skript += 'oLink.Save\n\n'

	lettersinuse = {}
	for key in mappings.keys():
		if mappings[key].get('letter'):
			if lettersinuse.get(mappings[key]['letter']):
				msg  = name + ": " + "the assigned letter "
				msg += "%s for share %s " % (mappings[key]['letter'], mappings[key]['server'])
				msg += "is already in use by share %s" % lettersinuse[mappings[key]['letter']]
				univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, msg)
			else:
				skript = skript + 'MapDrive "%s:","\\\\%s\\%s"\n' % (mappings[key]['letter'],mappings[key]['server'], key)
				lettersinuse[mappings[key]['letter']] = mappings[key]['server']

	homePath = ""
	if listener.baseConfig.has_key('samba/homedirletter') and listener.baseConfig['samba/homedirletter']:
		homePath = "%s:\Eigene Dateien" % listener.baseConfig['samba/homedirletter']

	if listener.baseConfig.has_key('ucsschool/userlogon/mysharespath') and listener.baseConfig['ucsschool/userlogon/mysharespath']:
		homePath = listener.baseConfig['ucsschool/userlogon/mysharespath']

	if homePath and listener.baseConfig.is_true('ucsschool/userlogon/myshares/enabled',False):
		skript = skript + '\n'
		skript = skript + 'SetMyShares "%s"\n' % homePath

	return skript

def writeWindowsLinkSkripts(uid, links, mappings):

	global scriptpath

	for path in scriptpath:
		script = generateWindowsLinkScript(desktopFolderName, links, mappings).replace('\n','\r\n')
		listener.setuid(0)
		try:
			fp = open("%s/%s.vbs" % (path, uid) ,'w')
			fp.write(script)
			fp.close()
		finally:
			listener.unsetuid()

def getConnection():
	if getConnection.connection is not None:
		return getConnection.connection
	connect_count = 0
	while connect_count < 31:
		try:
			getConnection.connection = connect()
			return getConnection.connection
		except ldap.LDAPError, msg:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: %s: failed to connect to ldap-server, wait..., ' % msg[0]['desc'])
			connect_count=connect_count+1
			if connect_count >= 30:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'ucsschool-user-logonscripts: %s: failed to connect to ldap-server, ' % msg[0]['desc'])
				raise
			else:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, 'ucsschool-user-logonscripts: Can not connect LDAP Server (%s), retry in 10 seconds' % msg[0]['desc'])
				time.sleep(10)
getConnection.connection = None


def groupchange(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: sync by group')
	if new:
		members = new.get('uniqueMember', ())
		if old and 'uniqueMember' in old:
			members = frozenset(members) ^ frozenset(old['uniqueMember'])
	elif old:
		members = old.get('uniqueMember', ())
	else:
		return
	for dn in members:
		if dn[:2].lower() != 'cn': # don't sync computer-accounts
			userchange(dn, 'search', {})

def sharechange(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: sync by share')
	if new:
		use = new
	elif old:
		use = old
	else:
		return

	l = getConnection()

	res = l.search(scope="sub", filter='(&(objectClass=posixGroup)(gidNumber=%s))' % use['univentionShareGid'][0])
	if len(res) > 0:
		dn = res[0][0]
		group = res[0][1]
		groupchange(dn, group, None)

def userGids(userdn):
	try:
		res_groups = getConnection().search(scope="sub", filter='(&(objectClass=posixGroup)(uniqueMember=%s))' % userdn, attr=['gidNumber'])
	except:
		univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'ucsschool-user-logonscripts: LDAP-search failed memberships of %s' % (dn))
		return frozenset()
	return frozenset([attributes['gidNumber'][0] for (dn, attributes, ) in res_groups])

def gidShares(gid):
	try:
		return getConnection().search(scope="sub", filter='(&(objectClass=univentionShareSamba)(univentionShareGid=%s))' % gid, attr=['cn','univentionShareHost','univentionShareSambaName'])
	except:
		univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN,
			'ucsschool-user-logonscripts: LDAP-search failed for shares with gid %s' % (gid))
		return ()

def userchange(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: sync by user')

	global scriptpath
	l = getConnection()

	if new:

		try:
			if new['uid'][0][-1] == "$": # machine account
				return
		except:
			pass
		ldapbase = listener.baseConfig['ldap/base']
		membershipIDs = set()

		if new == 'search': # called from groupchange
			try:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: got to search %s' % dn)
				res = l.search(base=dn, scope="base", filter='objectClass=*')
				if len(res) > 0:
					new = res[0][1]
					# get groups we are member of:
					membershipIDs.add(new['gidNumber'][0])
			except:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: LDAP-search failed for user %s' % (dn))
				return
		else:
			membershipIDs.add(new['gidNumber'][0])

		if old and \
			    new.get('uid') == old.get('uid') and \
			    new.get('gidNumber') == old.get('gidNumber') and \
			    new.get('homeDirectory') == old.get('homeDirectory'):
			return # skip unused attributes

		# Gruppen suchen mit uniqueMember=dn
		# shares suchen mit GID wie Gruppe
		univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: handle user %s' % dn)
		membershipIDs.update(userGids(dn))

		univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: groups are %s' % membershipIDs)


		mappings = {}
		classre = re.compile ('^cn=([^,]*),cn=klassen,cn=shares,ou=([^,]*),%s$' % ldapbase)
		links = {}
		validservers = frozenset(listener.baseConfig.get('ucsschool/userlogon/shares/validservers', listener.baseConfig.get('hostname') ).split(','))

		# get global links
		for name in globalLinks.keys():
			if globalLinks[name].get("server"):
				links[name] = globalLinks[name]["server"]
				if globalLinks[name].get("letter"):
					mappings[name] = {'server': globalLinks[name]["server"], 'letter': globalLinks[name]["letter"]}

		classShareLetter = listener.baseConfig.get('ucsschool/userlogon/classshareletter', 'K').replace(':', '')
		for ID in membershipIDs:
			for share in gidShares(ID):
				# linkname is identical to the sharename
				linkname = share[1]['cn'][0]
				if share[1].has_key('univentionShareSambaName'):
					linkname = share[1]['univentionShareSambaName'][0]

				# ignore link if already in global links
				if links.get(linkname):
					continue

				# hostname is either an IP or an FQDN
				hostname = share[1]['univentionShareHost'][0]
				if hostname.strip('012456789.'): # no IP-Address
					hostname = hostname.split('.', 1)[0]

				# save link and mapping
				if hostname in validservers or '*' in validservers:
					links[linkname] = hostname
					classmatches = classre.match(share[0])
					if classmatches and len(classmatches.groups()) == 2:
						mappings[linkname] = {'server': hostname, 'letter': classShareLetter}

		univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: links %s" % links)

		writeWindowsLinkSkripts(new['uid'][0], links, mappings)
		if listener.baseConfig.is_true("ucsschool/userlogon/mac"):
			writeMacLinkScripts(new['uid'][0], new['homeDirectory'][0], links)

	elif old and not new:
		for path in scriptpath:
			if os.path.exists("%s/%s.vbs" % (path, old['uid'][0])):
				os.remove("%s/%s.vbs" % (path, old['uid'][0]))


def handler(dn, new, old):

	getScriptPath()
	getGlobalLinks()

	# user or group?
	if dn[:3] == 'uid':
		userchange(dn, new, old)
	else:
		if (new and 'univentionShare' in new['objectClass']) or (old and 'univentionShare' in old['objectClass']):
			sharechange(dn, new, old)
		else:
			groupchange(dn, new, old)


def initialize():
	pass


def clean():

	global scriptpath

	listener.setuid(0)
	try:
		for path in scriptpath:
			if os.path.exists(path):
				for f in os.listdir(path):
					os.unlink(os.path.join(path, f))
	finally:
		listener.unsetuid()

def postrun():
	getConnection.connection = None
