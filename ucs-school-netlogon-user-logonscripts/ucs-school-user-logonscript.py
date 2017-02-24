# Univention UCS@school
#
# Copyright 2007-2017 Univention GmbH
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
import traceback
from ldap.filter import filter_format


name = 'ucs-school-user-logonscript'
description = 'Create user-specific netlogon-scripts'
filter = '(|(&(objectClass=posixAccount)(objectClass=organizationalPerson)(!(uid=*$)))(objectClass=posixGroup)(objectClass=univentionShare))'
attributes = []


# create netlogon scripts for samba3 and samba4


class Log(object):
	@classmethod
	def debug(cls, msg):
		cls.emit(univention.debug.ALL, msg)

	@staticmethod
	def emit(level, msg):
		univention.debug.debug(univention.debug.LISTENER, level, '{}: {}'.format(name, msg))

	@classmethod
	def error(cls, msg):
		cls.emit(univention.debug.ERROR, msg)

	@classmethod
	def info(cls, msg):
		cls.emit(univention.debug.INFO, msg)

	@classmethod
	def warn(cls, msg):
		cls.emit(univention.debug.WARN, msg)


class LDAPConnection(object):
	lo = None

	@staticmethod
	def connect():
		listener.setuid(0)
		try:
			return univention.uldap.getMachineConnection(ldap_master=False)
		finally:
			listener.unsetuid()

	def __enter__(self):
		if self.lo is not None:
			return self.lo

		connect_count = 0
		while connect_count < 31:
			try:
				LDAPConnection.lo = self.connect()
				return LDAPConnection.lo
			except ldap.LDAPError as ex:
				Log.warn('%s: failed to connect to LDAP server' % (ex[0]['desc'],))
				connect_count += 1
				if isinstance(ex, ldap.INVALID_CREDENTIALS):
					# this case may happen on rejoin during listener init; to shorten module init time, simply raise an exception
					Log.error('%s: giving up creating a new LDAP connection' % (ex[0]['desc'],))
					raise
				# in all other cases wait up to 300 seconds
				if connect_count >= 30:
					Log.error('%s: failed to connect to LDAP server' % (ex[0]['desc'],))
					raise
				else:
					Log.warn('unable to connect to LDAP server (%s), retrying in 10 seconds' % (ex[0]['desc'],))
					time.sleep(10)

	def __exit__(self, exc_type, exc_value, etraceback):
		if exc_type is None:
			return
		if isinstance(exc_value, ldap.LDAPError):
			LDAPConnection.lo = None
		Log.error('error=%r' % (exc_value,))
		Log.error(''.join(traceback.format_exception(exc_type, exc_value, etraceback)))


class UserLogonScriptListener(object):
	hostname = listener.baseConfig['hostname']
	domainname = listener.baseConfig['domainname']

	desktopFolderName = listener.configRegistry.get('ucsschool/userlogon/shares_foldername', "Eigene Shares")
	desktopFolderNameMacOS = listener.configRegistry.get('ucsschool/userlogon/mac/foldername', desktopFolderName)
	myshares_name = listener.configRegistry.get('ucsschool/userlogon/myshares/name', 'Eigene Dateien')
	mypictures_name = listener.configRegistry.get('ucsschool/userlogon/mypictures/name', 'Eigene Bilder')

	strTeacher = listener.baseConfig.get('ucsschool/ldap/default/container/teachers', 'lehrer')
	strStaff = listener.baseConfig.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
	ldapbase = listener.baseConfig.get('ldap/base', '')
	umcLink = listener.baseConfig.get(
		'ucsschool/userlogon/umclink/link',
		'http://%s.%s/univention-management-console' % (hostname, domainname))
	reTeacher = re.compile(listener.baseConfig.get(
		'ucsschool/userlogon/umclink/re',
		'^(.*),cn=(%s|%s),cn=users,ou=([^,]+),(?:ou=[^,]+,)?%s$' % (
			re.escape(strTeacher), re.escape(strStaff), re.escape(ldapbase))))
	filterTeacher = listener.baseConfig.get(
		'ucsschool/userlogon/umclink/filter',
		'(|(objectClass=ucsschoolTeacher)(objectClass=ucsschoolStaff))')

	_script_path = list()

	def __init__(self, dn, new, old):
		self.dn = dn
		self.new = new
		self.old = old
		self.global_links = self.get_global_links()

	@staticmethod
	def _mkdir(path):
		listener.setuid(0)
		try:
			if not os.path.isdir(path):
				os.makedirs(path)

			# copy the umc icon to the netlogon share, maybe there is a better way? ...
			if not os.path.isfile(os.path.join(path, "univention-management-console.ico")):
				shutil.copy("/usr/share/ucs-school-netlogon-user-logonscripts/univention-management-console.ico", path)
		finally:
			listener.unsetuid()

	@classmethod
	def get_script_path(cls):
		Log.warn('get_script_path()')
		if not cls._script_path:
			Log.warn('get_script_path() not cls._script_path')
			ucsschool_netlogon_path = listener.configRegistry.get('ucsschool/userlogon/netlogon/path', '').strip().rstrip('/')
			samba_netlogon_path = listener.configRegistry.get('samba/share/netlogon/path', '').strip().rstrip('/')
			cls._script_path = list()
			if ucsschool_netlogon_path:
				cls._script_path.append(ucsschool_netlogon_path)
			elif samba_netlogon_path:
				cls._script_path.append(samba_netlogon_path)
			else:
				cls._script_path.append("/var/lib/samba/netlogon/user")
				cls._script_path.append("/var/lib/samba/sysvol/%s/scripts/user" % listener.configRegistry.get('kerberos/realm', '').lower())

			for path in cls._script_path:
				cls._mkdir(path)
		return cls._script_path

	@staticmethod
	def get_global_links():
		Log.warn('get_global_links()')
		# search in baseconfig for shares which are common for all users
		global_links = dict()
		Log.info("search for global links")
		share_keys = [x.strip() for x in listener.baseConfig.get('ucsschool/userlogon/commonshares', '').split(',') if x.strip()]
		with LDAPConnection() as lo:
			for key in share_keys:
				# check if share exists
				try:
					if not lo.search(
							scope="sub",
							filter=filter_format(
								'(&(objectClass=univentionShareSamba)(|(cn=%s)(univentionShareSambaName=%s)))',
								(key, key)),
							attr=['cn']):
						continue
				except:
					continue
				Log.info("search global links for %s" % key)
				server = listener.baseConfig.get('ucsschool/userlogon/commonshares/server/%s' % key)
				letter = listener.baseConfig.get('ucsschool/userlogon/commonshares/letter/%s' % key, '').replace(':', '')
				if server:
					global_links[key] = {'server': server}
					if letter:
						global_links[key]['letter'] = letter
		Log.info("got global links %s" % global_links)
		return global_links

	@staticmethod
	def generate_mac_script(uid, name, host):
		return '''#!/usr/bin/osascript
tell application "Finder"
open location "smb://%s@%s/%s"
activate
end tell
''' % (uid, host, name)

	@classmethod
	def write_mac_link_scripts(cls, uid, homepath, links):
		listener.setuid(0)
		try:
			if not (os.path.exists(homepath) and not os.path.isdir(homepath)):  # may be /dev/null
				# check existence of home
				uidnumber = 0
				gidnumber = 0
				try:
					uidnumber = pwd.getpwnam(uid)[2]
					gidnumber = pwd.getpwnam(uid)[3]
				except:
					pass

				if not os.path.exists(os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS)):
					if not os.path.exists(homepath):
						os.mkdir(homepath, 0o700)
						os.chown(homepath, uidnumber, gidnumber)

					for path in [os.path.join(homepath, "Desktop"), os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS)]:
						if not os.path.exists(path):
							os.mkdir(path)
							os.chown(path, uidnumber, gidnumber)

				# remove old scripts
				for filename in os.listdir(os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS)):
					try:
						if os.path.isdir(os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS, filename)):
							shutil.rmtree(os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS, filename))
						else:
							os.remove(os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS, filename))
					except:
						Log.error("failed to remove %s" % filename)
						raise

				for filename in links:
					macscriptpath = os.path.join(homepath, "Desktop", cls.desktopFolderNameMacOS, "%s.app" % filename)
					os.mkdir(macscriptpath)
					os.chown(macscriptpath, uidnumber, gidnumber)
					macscriptfile = os.path.join(macscriptpath, filename)
					fp = open(macscriptfile, 'w')
					fp.write(cls.generate_mac_script(uid, filename, links[filename]))
					fp.close()
					os.chmod(macscriptfile, 0o700)
					os.chown(macscriptfile, uidnumber, gidnumber)
		finally:
			listener.unsetuid()

	@classmethod
	def generate_windows_link_script(cls, desktopfolder, links, mappings, dn):
		Log.warn('generate_windows_link_script()')
		# desktopfolder is a strings, links is a list of tupels which contain linkname and linkgoal
		skript = '''Const DESKTOP = &H10&
Const FolderName = "{desktop_folder_name}"
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
 Set objReg = GetObject("winmgmts:{{impersonationLevel=impersonate}}!" & strComputer & "\\root\\default:StdRegProv")

 \' Check if folder {myshares_name} exists
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

 \' Check if folder {mypictures_name} exists
 Set fso = CreateObject("Scripting.FileSystemObject")
 If not (fso.FolderExists(strPersonal & "\{mypictures_name}")) then
	 ON ERROR RESUME NEXT
	 Set f = fso.CreateFolder(strPersonal & "\{mypictures_name}")
 End If

 intRet3= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath1, "My Pictures", strPersonal & "\{mypictures_name}")
 If intRet3 <> 0 Then
	Wscript.echo "Error: Setting Shell Folder Key Personal"
 End If

 intRet4= objReg.SetStringValue(HKEY_CURRENT_USER, strKeyPath2, "My Pictures", strPersonal & "\{mypictures_name}")
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

'''.format(
	desktop_folder_name=desktopfolder.translate(None, '\/:*?"<>|'),
	myshares_name=cls.myshares_name,
	mypictures_name=cls.mypictures_name)

		# create shortcuts to shares
		for linkName in links:
			skript += '''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = FolderPath + "\\{link_name}.LNK"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "\\\\{links_link_name}\\{link_name}"
oLink.Save

'''.format(link_name=linkName, links_link_name=links[linkName])

		# create shortcut to umc for teachers
		with LDAPConnection() as lo:
			try:
				is_teacher = bool(lo.search(base=dn, scope='base', filter=cls.filterTeacher)[0])
			except (ldap.NO_SUCH_OBJECT, IndexError):
				is_teacher = False
			if not is_teacher:
				is_teacher = cls.reTeacher.match(dn)  # old format before migration
		if is_teacher:
			skript += '''Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strLinkPath = WshShell.SpecialFolders("Desktop") & "\Univention Management Console.URL"
If Not objFSO.FileExists(strLinkPath) Then
	Set oUrlLink = WshShell.CreateShortcut(strLinkPath)
	oUrlLink.TargetPath = "{umc_link}"
	oUrlLink.Save
	set objFile = objFSO.OpenTextFile(strLinkPath, 8, True)
	objFile.WriteLine("IconFile=\\\\{hostname}.{domainname}\\netlogon\\user\\univention-management-console.ico")
	objFile.WriteLine("IconIndex=0")
	objFile.Close

End If
'''.format(umc_link=cls.umcLink, hostname=cls.hostname, domainname=cls.domainname)

		lettersinuse = {}
		for key in mappings.keys():
			if mappings[key].get('letter'):
				if lettersinuse.get(mappings[key]['letter']):
					if lettersinuse[mappings[key]['letter']] == mappings[key]['server']:
						continue
					Log.warn(
						'{name}: the assigned letter {letter!r} for share \\{server}\{key} is already in use by '
						'server "{lettersinuse!r}"'.format(
							name=name,
							letter=mappings[key]['letter'],
							server=mappings[key]['server'],
							key=key,
							lettersinuse=lettersinuse[mappings[key]['letter']]))
				else:
					skript += 'MapDrive "%s:","\\\\%s\\%s"\n' % (mappings[key]['letter'], mappings[key]['server'], key)
					lettersinuse[mappings[key]['letter']] = mappings[key]['server']

		homePath = ""
		if listener.baseConfig.get('samba/homedirletter'):
			homePath = "{}:\{}".format(listener.baseConfig['samba/homedirletter'], cls.myshares_name)

		if listener.baseConfig.get('ucsschool/userlogon/mysharespath'):
			homePath = listener.baseConfig['ucsschool/userlogon/mysharespath']

		if homePath and listener.baseConfig.is_true('ucsschool/userlogon/myshares/enabled', False):
			skript += '\n'
			skript += 'SetMyShares "%s"\n' % homePath

		return skript

	def write_windows_link_skripts(self, uid, links, mappings):
		Log.warn('write_windows_link_skripts()')
		for path in self.get_script_path():
			script = self.generate_windows_link_script(self.desktopFolderName, links, mappings, self.dn).replace('\n', '\r\n')
			listener.setuid(0)
			try:
				filepath = "%s/%s.vbs" % (path, uid)
				with open(filepath, 'w') as fp:
					fp.write(script)
				os.chmod(filepath, 0o755)
			finally:
				listener.unsetuid()

	def group_change(self, new, old):
		"""
		Please explain what this should do!
		'new' may be a dict from an ldap search
		'old' may not be a dict but None

		# TODO: fix arguments and branch on real booleans

		:param new: self.group_change(group, None)  # called from share_change()
		:param old: may be set to None in share_change()
		"""
		Log.info('sync by group')
		Log.warn('group_change()')
		if new:
			members = self.new.get('uniqueMember', ())
			if old and 'uniqueMember' in old:
				members = frozenset(members) ^ frozenset(old['uniqueMember'])
		elif self.old:
			members = old.get('uniqueMember', ())
		else:
			return
		for self.dn in members:
			if self.dn[:2].lower() != 'cn':  # don't sync computer-accounts
				self.user_change('search', {})

	def share_change(self):
		Log.info('sync by share')
		Log.warn('share_change()')
		if self.new:
			use = self.new
		elif self.old:
			use = self.old
		else:
			return

		try:
			with LDAPConnection() as lo:
				res = lo.search(
					scope="sub",
					filter=filter_format('(&(objectClass=posixGroup)(gidNumber=%s))', (use['univentionShareGid'][0],)))
				if len(res) > 0:
					dn = res[0][0]
					group = res[0][1]
					self.group_change(group, None)
		except ldap.LDAPError as msg:
			Log.error("ldap search for group object with gidNumber=%r failed in share_change(%s) (%s)" % (
				use['univentionShareGid'][0], self.dn, msg))
			raise

	@staticmethod
	def user_gids(dn):
		try:
			with LDAPConnection() as lo:
				res = lo.search(
					scope="sub",
					filter=filter_format("(&(objectClass=posixGroup)(uniqueMember=%s))", (dn,)),
					attr=["gidNumber"])
				return frozenset([attributes['gidNumber'][0] for (dn_, attributes, ) in res])
		except ldap.LDAPError as msg:
			Log.error("ldap search for %s failed in user_gids() (%s)" % (dn, msg))
		return frozenset()

	@staticmethod
	def gid_shares(gid):
		try:
			with LDAPConnection() as lo:
				return lo.search(
					scope="sub",
					filter=filter_format('(&(objectClass=univentionShareSamba)(univentionShareGid=%s))', (gid,)),
					attr=['cn', 'univentionShareHost', 'univentionShareSambaName'])
		except ldap.LDAPError as msg:
			Log.warn('LDAP-search failed for shares with gid %s: %r' % (gid, msg))
			return ()

	def user_change(self, new, old):
		"""
		Please explain what this should do!
		'new' may not be a dict but a string

		# TODO: fix arguments and branch on real booleans

		:param new: if new == 'search':  # called from group_change()
		:param old: may be set to {} in group_change()
		"""
		Log.info('sync by user')
		Log.warn('user_change()')
		Log.debug('self.dn=%r' % (self.dn,))
		Log.debug('new=%r' % (new,))
		Log.debug('old=%r' % (old,))

		with LDAPConnection() as lo:
			if new:
				try:
					if new['uid'][0][-1] == "$":  # machine account
						return
				except:
					pass
				ldapbase = listener.baseConfig['ldap/base']
				membershipIDs = set()

				if new == 'search':  # called from group_change
					try:
						Log.info('got to search %s' % (self.dn,))
						res = lo.search(base=self.dn, scope="base", filter='objectClass=*')
						if len(res) > 0:
							new = res[0][1]
							# get groups we are member of:
							membershipIDs.add(new['gidNumber'][0])
					except ldap.NO_SUCH_OBJECT:
						Log.info('user_change(): user %r not found' % (self.dn,))
						return
					except Exception:
						Log.error('LDAP-search failed for user %s in user_change()' % (self.dn,))
						raise
				else:
					membershipIDs.add(new['gidNumber'][0])

				if old and new.get('uid') == old.get('uid') and new.get('gidNumber') == old.get('gidNumber') and new.get('homeDirectory') == old.get('homeDirectory'):
					return  # skip unused attributes

				# Gruppen suchen mit uniqueMember=dn
				# shares suchen mit GID wie Gruppe
				Log.info('handle user %s' % (self.dn,))
				membershipIDs.update(self.user_gids(self.dn))

				Log.info('groups are %s' % (membershipIDs,))

				mappings = {}
				classre = re.compile('^cn=([^,]*),cn=klassen,cn=shares,ou=([^,]*),(?:ou=[^,]+,)?%s$' % re.escape(ldapbase))
				links = {}
				validservers = frozenset(listener.baseConfig.get(
					'ucsschool/userlogon/shares/validservers',
					self.hostname
				).split(','))

				# get global links
				for name in self.global_links.keys():
					if self.global_links[name].get("server"):
						links[name] = self.global_links[name]["server"]
						if self.global_links[name].get("letter"):
							mappings[name] = {
								'server': self.global_links[name]["server"],
								'letter': self.global_links[name]["letter"],
							}

				classShareLetter = listener.baseConfig.get('ucsschool/userlogon/classshareletter', 'K').replace(':', '')
				for ID in membershipIDs:
					for share in self.gid_shares(ID):
						# linkname is identical to the sharename
						linkname = share[1]['cn'][0]
						if 'univentionShareSambaName' in share[1]:
							linkname = share[1]['univentionShareSambaName'][0]

						# ignore link if already in global links
						if links.get(linkname):
							continue

						# hostname_ is either an IP or an FQDN
						hostname_ = share[1]['univentionShareHost'][0]
						if hostname_.strip('012456789.'):  # no IP-Address
							hostname_ = hostname_.split('.', 1)[0]

						# save link and mapping
						if hostname_ in validservers or '*' in validservers:
							links[linkname] = hostname_
							classmatches = classre.match(share[0])
							if classmatches and len(classmatches.groups()) == 2:
								mappings[linkname] = {'server': hostname_, 'letter': classShareLetter}

				Log.info("links %s" % (links,))

				self.write_windows_link_skripts(new['uid'][0], links, mappings)
				if listener.baseConfig.is_true("ucsschool/userlogon/mac"):
					self.write_mac_link_scripts(new['uid'][0], new['homeDirectory'][0], links)

			elif old and not new:
				listener.setuid(0)
				try:
					for path in self.get_script_path():
						if os.path.exists("%s/%s.vbs" % (path, old['uid'][0])):
							os.remove("%s/%s.vbs" % (path, old['uid'][0]))
				finally:
					listener.unsetuid()


def handler(dn, new, old):
	object_class = new.get('objectClass', []) or old.get('objectClass', [])
	Log.warn('objectClass={!r}\n\nold={!r}\n\nnew={!r}'.format(object_class, old, new))
	script_handler = UserLogonScriptListener(dn, new, old)
	if 'posixAccount' in object_class:
		script_handler.user_change(new, old)
	elif 'univentionShare' in object_class:
		script_handler.share_change()
	elif 'posixGroup' in object_class:
		script_handler.group_change(new, old)
	else:
		raise RuntimeError('Unknown object. objectClass={!r}\n\nold={!r}\n\nnew={!r}'.format(object_class, old, new))


def clean():
	listener.setuid(0)
	try:
		for path in UserLogonScriptListener.get_script_path():
			if os.path.exists(path):
				for f in os.listdir(path):
					os.unlink(os.path.join(path, f))
	finally:
		listener.unsetuid()


def postrun():
	LDAPConnection.lo = None
