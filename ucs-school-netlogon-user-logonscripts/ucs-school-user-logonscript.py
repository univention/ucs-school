# Univention UCS@School
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
import univention.debug
import univention.uldap

import os
import pwd
import re
import time
import shutil
import ldap
from ldap.filter import filter_format

hostname = listener.baseConfig['hostname']
domainname = listener.baseConfig['domainname']
ip = listener.baseConfig['interfaces/eth0/address']

name = 'ucs-school-user-logonscript'
description = 'Create user-specific netlogon-scripts'
filter = '(|(&(objectClass=posixAccount)(objectClass=organizationalPerson)(!(uid=*$)))(objectClass=posixGroup)(objectClass=univentionShare))'
atributes = []

scriptpath = []
desktopFolderName = "Eigene Shares"
desktopFolderNameMacOS = listener.configRegistry.get('ucsschool/userlogon/mac/foldername', desktopFolderName)
globalLinks = {}

strTeacher = listener.baseConfig.get('ucsschool/ldap/default/container/teachers', 'lehrer')
strStaff = listener.baseConfig.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
ldapbase = listener.baseConfig.get('ldap/base', '')
umcLink = listener.baseConfig.get('ucsschool/userlogon/umclink/link', 'http://%s.%s/univention-management-console' % (hostname, domainname))
reTeacher = re.compile(listener.baseConfig.get('ucsschool/userlogon/umclink/re', '^(.*),cn=(%s|%s),cn=users,ou=([^,]+),(?:ou=[^,]+,)?%s$' % (re.escape(strTeacher), re.escape(strStaff), re.escape(ldapbase))))
filterTeacher = listener.baseConfig.get('ucsschool/userlogon/umclink/filter', '(|(objectClass=ucsschoolTeacher)(objectClass=ucsschoolStaff))')

# create netlogon scripts for samba3 and samba4
def getScriptPath():

	global scriptpath

	if scriptpath:
		return

	ucsschool_netlogon_path = listener.configRegistry.get('ucsschool/userlogon/netlogon/path', '').strip().rstrip('/')
	samba_netlogon_path = listener.configRegistry.get('samba/share/netlogon/path', '').strip().rstrip('/')
	if ucsschool_netlogon_path:
		scriptpath.append(ucsschool_netlogon_path)
	elif samba_netlogon_path:
		scriptpath.append(samba_netlogon_path)
	else:
		scriptpath.append("/var/lib/samba/netlogon/user")
		scriptpath.append("/var/lib/samba/sysvol/%s/scripts/user" % listener.configRegistry.get('kerberos/realm', '').lower())

	for path in scriptpath:
			listener.setuid(0)
			try:
				if not os.path.isdir(path):
					os.makedirs(path)

				# copy the umc icon to the netlogon share, maybe there is a better way? ...
				if not os.path.isfile(os.path.join(path, "univention-management-console.ico")):
					shutil.copy("/usr/share/ucs-school-netlogon-user-logonscripts/univention-management-console.ico", path)
			finally:
				listener.unsetuid()


def getCommandOutput(command):
	child = os.popen(command)
	data = child.read()
	err = child.close()
	if err:
		raise RuntimeError('%s failed with exit code %d' % (command, err))
	return data


def connect():
	connection = None
	listener.setuid(0)
	try:
		connection = univention.uldap.getMachineConnection(ldap_master=False)
	finally:
		listener.unsetuid()
	return connection


def getGlobalLinks():
	# search in baseconfig for shares which are common for all users
	share_keys = []
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: search for global links")
	if listener.baseConfig.get('ucsschool/userlogon/commonshares'):
		with LDAPConnection() as lo:
			share_keys = listener.baseConfig['ucsschool/userlogon/commonshares'].split(',')
			for key in share_keys:
				# check if share exists
				try:
					if not lo.search(scope="sub", filter=filter_format('(&(objectClass=univentionShareSamba)(|(cn=%s)(univentionShareSambaName=%s)))', (key, key)), attr=['cn']):
						continue
				except:
					continue
				univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: search global links for %s" % key)
				server = listener.baseConfig.get('ucsschool/userlogon/commonshares/server/%s' % key)
				letter = listener.baseConfig.get('ucsschool/userlogon/commonshares/letter/%s' % key, '').replace(':', '')
				if server:
					globalLinks[key] = {'server': server}
					if letter:
						globalLinks[key]['letter'] = letter
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, "ucsschool-user-logonscripts: got global links %s" % globalLinks)


def generateMacScript(uid, name, host):
	return '''#!/usr/bin/osascript
tell application "Finder"
 open location "smb://%s@%s/%s"
 activate
end tell
''' % (uid, host, name)


def writeMacLinkScripts(uid, homepath, links):
	listener.setuid(0)
	try:
		if not (os.path.exists(homepath) and not os.path.isdir(homepath)): # may be /dev/null
			# check existence of home
			uidnumber = 0
			gidnumber = 0
			try:
				uidnumber = pwd.getpwnam(uid)[2]
				gidnumber = pwd.getpwnam(uid)[3]
			except:
				pass

			if not os.path.exists(os.path.join(homepath, "Desktop", desktopFolderNameMacOS)):
				if not os.path.exists(homepath):
					os.mkdir(homepath, 0o700)
					os.chown(homepath, uidnumber, gidnumber)

				for path in [os.path.join(homepath, "Desktop"), os.path.join(homepath, "Desktop", desktopFolderNameMacOS)]:
					if not os.path.exists(path):
						os.mkdir(path)
						os.chown(path, uidnumber, gidnumber)

			# remove old scripts
			for file in os.listdir(os.path.join(homepath, "Desktop", desktopFolderNameMacOS)):
				try:
					if os.path.isdir(os.path.join(homepath, "Desktop", desktopFolderNameMacOS, file)):
						shutil.rmtree(os.path.join(homepath, "Desktop", desktopFolderNameMacOS, file))
					else:
						os.remove(os.path.join(homepath, "Desktop", desktopFolderNameMacOS, file))
				except:
					univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, "ucsschool-user-logonscripts: failed to remove %s" % file)
					raise

			for name in links:
				macscriptpath = os.path.join(homepath, "Desktop", desktopFolderNameMacOS, "%s.app" % name)
				os.mkdir(macscriptpath)
				os.chown(macscriptpath, uidnumber, gidnumber)
				macscriptfile = os.path.join(macscriptpath, name)
				fp = open(macscriptfile, 'w')
				fp.write(generateMacScript(uid, name, links[name]))
				fp.close()
				os.chmod(macscriptfile, 0o700)
				os.chown(macscriptfile, uidnumber, gidnumber)
	finally:
			listener.unsetuid()


def generateWindowsLinkScript(desktopfolder, links, mappings, dn):
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

	# create shortcut to umc for teachers
	is_teacher = reTeacher.match(dn)
	if not is_teacher:
		with LDAPConnection() as lo:
			try:
				is_teacher = bool(lo.search(base=dn, scope='base', filter=filterTeacher)[0])
			except (ldap.NO_SUCH_OBJECT, IndexError):
				pass
	if is_teacher:
		skript += 'Set WshShell = CreateObject("WScript.Shell")\n'
		skript += 'Set objFSO = CreateObject("Scripting.FileSystemObject")\n'
		skript += 'strLinkPath = WshShell.SpecialFolders("Desktop") & "\Univention Management Console.URL"\n'
		skript += 'If Not objFSO.FileExists(strLinkPath) Then\n'
		skript += '	Set oUrlLink = WshShell.CreateShortcut(strLinkPath)\n'
		skript += '	oUrlLink.TargetPath = "%s"\n' % umcLink
		skript += '	oUrlLink.Save\n'
		skript += '	set objFile = objFSO.OpenTextFile(strLinkPath, 8, True)\n'
		skript += '	objFile.WriteLine("IconFile=\\\\%s.%s\\netlogon\\user\\univention-management-console.ico")\n' % (hostname, domainname)
		skript += '	objFile.WriteLine("IconIndex=0")\n'
		skript += '	objFile.Close\n\n'
		skript += 'End If\n'

	lettersinuse = {}
	for key in mappings.keys():
		if mappings[key].get('letter'):
			if lettersinuse.get(mappings[key]['letter']):
				if lettersinuse[mappings[key]['letter']] == mappings[key]['server']:
					continue
				msg = name + ": " + "the assigned letter "
				msg += "%r for share \\%s\%s " % (mappings[key]['letter'], mappings[key]['server'], key)
				msg += "is already in use by server %r" % (lettersinuse[mappings[key]['letter']],)
				univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, msg)
			else:
				skript = skript + 'MapDrive "%s:","\\\\%s\\%s"\n' % (mappings[key]['letter'], mappings[key]['server'], key)
				lettersinuse[mappings[key]['letter']] = mappings[key]['server']

	homePath = ""
	if listener.baseConfig.get('samba/homedirletter'):
		homePath = "%s:\Eigene Dateien" % listener.baseConfig['samba/homedirletter']

	if listener.baseConfig.get('ucsschool/userlogon/mysharespath'):
		homePath = listener.baseConfig['ucsschool/userlogon/mysharespath']

	if homePath and listener.baseConfig.is_true('ucsschool/userlogon/myshares/enabled', False):
		skript = skript + '\n'
		skript = skript + 'SetMyShares "%s"\n' % homePath

	return skript


def writeWindowsLinkSkripts(uid, links, mappings, dn):

	global scriptpath

	for path in scriptpath:
		script = generateWindowsLinkScript(desktopFolderName, links, mappings, dn).replace('\n', '\r\n')
		listener.setuid(0)
		try:
			filepath = "%s/%s.vbs" % (path, uid)
			with open(filepath, 'w') as fp:
				fp.write(script)
			os.chmod(filepath, 0o755)
		finally:
			listener.unsetuid()


class LDAPConnection(object):
	lo = None

	def __enter__(self):
		if self.lo is not None:
			return self.lo

		connect_count = 0
		while connect_count < 31:
			try:
				LDAPConnection.lo = connect()
				return LDAPConnection.lo
			except ldap.LDAPError as ex:
				univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, 'ucsschool-user-logonscripts: %s: failed to connect to LDAP server' % (ex[0]['desc'],))
				connect_count = connect_count + 1
				if isinstance(ex, ldap.INVALID_CREDENTIALS):
					# this case may happen on rejoin during listener init; to shorten module init time, simply raise an exception
					univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'ucsschool-user-logonscripts: %s: giving up creating a new LDAP connection' % (ex[0]['desc'],))
					raise
				# in all other cases wait up to 300 seconds
				if connect_count >= 30:
					univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'ucsschool-user-logonscripts: %s: failed to connect to LDAP server' % (ex[0]['desc'],))
					raise
				else:
					univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, 'ucsschool-user-logonscripts: unable to connect to LDAP server (%s), retrying in 10 seconds' % (ex[0]['desc'],))
					time.sleep(10)

	def __exit__(self, exc_type, exc_value, traceback):
		if exc_type is not None and isinstance(exc_type, type(ldap.LDAPError)):
			LDAPConnection.lo = None
			univention.debug.debug(univention.debug.LISTENER, univention.debug.ERROR, 'ucsschool-user-logonscripts: a LDAP error occurred - invalidating LDAP connection - error=%r' % (exc_value[0]['desc'],))


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

	try:
		with LDAPConnection() as lo:
			res = lo.search(scope="sub", filter=filter_format('(&(objectClass=posixGroup)(gidNumber=%s))', (use['univentionShareGid'][0],)))
			if len(res) > 0:
				dn = res[0][0]
				group = res[0][1]
				groupchange(dn, group, None)
	except ldap.LDAPError as msg:
		univention.debug.debug(
			univention.debug.LISTENER,
			univention.debug.ERROR,
			"ucsschool-user-logonscripts: ldap search for group object with gidNumber=%r failed in sharechange(%s) (%s)" % (use['univentionShareGid'][0], dn, msg))
		raise


def userGids(dn):

	try:
		with LDAPConnection() as lo:
			res = lo.search(scope="sub", filter=filter_format("(&(objectClass=posixGroup)(uniqueMember=%s))", (dn,)), attr=["gidNumber"])
			return frozenset([attributes['gidNumber'][0] for (dn_, attributes, ) in res])
	except ldap.LDAPError as msg:
		univention.debug.debug(
			univention.debug.LISTENER,
			univention.debug.ERROR,
			"ucsschool-user-logonscripts: ldap search for %s failed in userGids() (%s)" % (dn, msg))
	return frozenset()


def gidShares(gid):
	try:
		with LDAPConnection() as lo:
			return lo.search(scope="sub", filter=filter_format('(&(objectClass=univentionShareSamba)(univentionShareGid=%s))', (gid,)), attr=['cn', 'univentionShareHost', 'univentionShareSambaName'])
	except ldap.LDAPError as msg:
		univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN,
			'ucsschool-user-logonscripts: LDAP-search failed for shares with gid %s: %r' % (gid, msg))
		return ()


def userchange(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: sync by user')

	global scriptpath

	with LDAPConnection() as lo:

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
					res = lo.search(base=dn, scope="base", filter='objectClass=*')
					if len(res) > 0:
						new = res[0][1]
						# get groups we are member of:
						membershipIDs.add(new['gidNumber'][0])
				except:
					univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, 'ucsschool-user-logonscripts: LDAP-search failed for user %s in userchange()' % (dn))
					raise
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
			classre = re.compile('^cn=([^,]*),cn=klassen,cn=shares,ou=([^,]*),(?:ou=[^,]+,)?%s$' % re.escape(ldapbase))
			links = {}
			validservers = frozenset(listener.baseConfig.get('ucsschool/userlogon/shares/validservers', listener.baseConfig.get('hostname')).split(','))

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
					if 'univentionShareSambaName' in share[1]:
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

			writeWindowsLinkSkripts(new['uid'][0], links, mappings, dn)
			if listener.baseConfig.is_true("ucsschool/userlogon/mac"):
				writeMacLinkScripts(new['uid'][0], new['homeDirectory'][0], links)

		elif old and not new:
			listener.setuid(0)
			try:
				for path in scriptpath:
					if os.path.exists("%s/%s.vbs" % (path, old['uid'][0])):
						os.remove("%s/%s.vbs" % (path, old['uid'][0]))
			finally:
				listener.unsetuid()


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
	LDAPConnection.lo = None
