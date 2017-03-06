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
import copy
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
	hostname = listener.configRegistry['hostname']
	domainname = listener.configRegistry['domainname']

	desktop_folder_path = listener.configRegistry.get('ucsschool/userlogon/shares_folder_parent_path')
	if desktop_folder_path:
		desktop_folder_path = desktop_folder_path.strip('"').rstrip('\\')
		desktop_folder_path = 'oShellScript.ExpandEnvironmentStrings("{}")'.format(desktop_folder_path)
	else:
		desktop_folder_path = 'objFolderItem.Path'
	desktop_folder_name = listener.configRegistry.get('ucsschool/userlogon/shares_foldername', 'Eigene Shares')
	desktop_folder_name_macos = listener.configRegistry.get('ucsschool/userlogon/mac/foldername', desktop_folder_name)
	desktop_folder_icon = listener.configRegistry.get('ucsschool/userlogon/shares_folder_icon')  # '%SystemRoot%\system32\imageres.dll,143'
	my_files_link_name = listener.configRegistry.get('ucsschool/userlogon/my_files_link_name', 'Meine Dateien')
	my_files_link_icon = listener.configRegistry.get('ucsschool/userlogon/my_files_link_icon')  # '%SystemRoot%\system32\imageres.dll,207'
	other_links_icon = listener.configRegistry.get('ucsschool/userlogon/other_links_icon')  # '%SystemRoot%\system32\imageres.dll,193'
	myshares_name = listener.configRegistry.get('ucsschool/userlogon/myshares/name', 'Eigene Dateien')
	mypictures_name = listener.configRegistry.get('ucsschool/userlogon/mypictures/name', 'Eigene Bilder')
	create_drive_mappings = listener.configRegistry.is_true('ucsschool/userlogon/create_drive_mappings', True)
	create_myfiles_link = listener.configRegistry.is_true('ucsschool/userlogon/create_myfiles_link', True)
	create_personal_files_mapping = listener.configRegistry.is_true('ucsschool/userlogon/myshares/enabled', False)
	create_shortcuts = listener.configRegistry.is_true('ucsschool/userlogon/create_shortcuts', True)
	create_teacher_umc_link = listener.configRegistry.is_true('ucsschool/userlogon/create_teacher_umc_link', True)

	strTeacher = listener.configRegistry.get('ucsschool/ldap/default/container/teachers', 'lehrer')
	strStaff = listener.configRegistry.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
	ldapbase = listener.configRegistry.get('ldap/base', '')
	umcLink = listener.configRegistry.get(
		'ucsschool/userlogon/umclink/link',
		'http://%s.%s/univention-management-console' % (hostname, domainname))
	reTeacher = re.compile(listener.configRegistry.get(
		'ucsschool/userlogon/umclink/re',
		'^(.*),cn=(%s|%s),cn=users,ou=([^,]+),(?:ou=[^,]+,)?%s$' % (
			re.escape(strTeacher), re.escape(strStaff), re.escape(ldapbase))))
	filterTeacher = listener.configRegistry.get(
		'ucsschool/userlogon/umclink/filter',
		'(|(objectClass=ucsschoolTeacher)(objectClass=ucsschoolStaff))')
	template_paths = dict(
		main='/usr/share/ucs-school-netlogon-user-logonscripts/net-logon-script.vbs',
		shortcut_to_share='/usr/share/ucs-school-netlogon-user-logonscripts/shortcut-to-share.vbs',
		teacher_umc_link='/usr/share/ucs-school-netlogon-user-logonscripts/teacher-umc-link.vbs',
		mac_script='/usr/share/ucs-school-netlogon-user-logonscripts/mac_script',
	)
	_disabled_share_links = dict()
	_template_cache = dict()
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
	def get_disabled_share_links(cls):
		if not cls._disabled_share_links:
			for k, v in listener.configRegistry.items():
				if k.startswith('ucsschool/userlogon/disabled_share_links/'):
					server = k.rpartition('/')[-1]
					shares = [l.strip().rstrip('/') for l in v.split(',')]
					cls._disabled_share_links[server] = shares
		return cls._disabled_share_links

	@classmethod
	def get_script_path(cls):
		if not cls._script_path:
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
		# search in configRegistry for shares which are common for all users
		global_links = dict()
		Log.info("search for global links")
		share_keys = [x.strip() for x in listener.configRegistry.get('ucsschool/userlogon/commonshares', '').split(',') if x.strip()]
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
				server = listener.configRegistry.get('ucsschool/userlogon/commonshares/server/%s' % key)
				letter = listener.configRegistry.get('ucsschool/userlogon/commonshares/letter/%s' % key, '').replace(':', '')
				if server:
					global_links[key] = {'server': server}
					if letter:
						global_links[key]['letter'] = letter
		Log.info("got global links %s" % global_links)
		return global_links

	@classmethod
	def get_home_path(cls):
		res = ''
		if listener.configRegistry.get('samba/homedirletter'):
			res = "{}:\{}".format(listener.configRegistry['samba/homedirletter'], cls.myshares_name)
		if listener.configRegistry.get('ucsschool/userlogon/mysharespath'):
			res = listener.configRegistry['ucsschool/userlogon/mysharespath']
		return res

	@classmethod
	def generate_mac_script(cls, uid, name, host):
		return cls.get_logon_template(cls.template_paths['mac_script']).format(uid=uid, host=host, name=name)

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

				if not os.path.exists(os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos)):
					if not os.path.exists(homepath):
						os.mkdir(homepath, 0o700)
						os.chown(homepath, uidnumber, gidnumber)

					for path in [os.path.join(homepath, "Desktop"), os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos)]:
						if not os.path.exists(path):
							os.mkdir(path)
							os.chown(path, uidnumber, gidnumber)

				# remove old scripts
				for filename in os.listdir(os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos)):
					try:
						if os.path.isdir(os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos, filename)):
							shutil.rmtree(os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos, filename))
						else:
							os.remove(os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos, filename))
					except:
						Log.error("failed to remove %s" % filename)
						raise

				for filename in links:
					macscriptpath = os.path.join(homepath, "Desktop", cls.desktop_folder_name_macos, "%s.app" % filename)
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
	def get_logon_template(cls, path, format_dict=None, no_icons=None):
		"""
		Fetch a VBS/mac template and apply text replacements.

		:param path: str: path to template file
		:param format_dict: dict: if not None, text replacements will be
		applied with str.format(**format_dict). Attention: templates will be
		cached. They can be "compiled" with format_dict only once! Use None to
		format them individually.
		:param no_icons: list of strings: remove lines that contain the listed
		format-keys (e.g. 'my_files_link_icon' to remove icon from My Files
		link).
		:return: str: template text
		"""
		if path not in cls._template_cache:
			# read file into list of strings
			with open(path, 'rb') as fp:
				tmp = fp.readlines()
			# remove icon lines
			for key in (no_icons or list()):
				try:
					del format_dict[key]
				except KeyError:  # key not in format_dict
					pass
				except TypeError:  # format_dict is None
					pass
				for line in tmp:
					if '{%s}' % key in line:
						tmp.remove(line)
			# list 2 string
			tmp = ''.join(tmp)
			# format string
			if format_dict:
				assert isinstance(format_dict, dict)
				tmp = tmp.format(**format_dict)
			cls._template_cache[path] = tmp
		# return a copy, so string in cache will not be modified
		return copy.copy(cls._template_cache[path])

	@classmethod
	def generate_drive_mappings_snippet(cls, mappings):
		res = ''
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
					res += 'MapDrive "%s:","\\\\%s\\%s"\n' % (mappings[key]['letter'], mappings[key]['server'], key)
					lettersinuse[mappings[key]['letter']] = mappings[key]['server']
		return res

	@classmethod
	def generate_header_and_functions_snippet(cls):
		str_replacements = dict(
			desktop_folder_icon=cls.desktop_folder_icon,
			desktop_folder_name=cls.desktop_folder_name.translate(None, '\/:*?"<>|'),
			desktop_folder_path=cls.desktop_folder_path,
			domainname=cls.domainname,
			hostname=cls.hostname,
			my_files_link_icon=cls.my_files_link_icon,
			my_files_link_name=cls.my_files_link_name,
			mypictures_name=cls.mypictures_name,
			myshares_name=cls.myshares_name,
			other_links_icon=cls.other_links_icon,
			umc_link=cls.umcLink,
		)
		no_icons = list()
		if not cls.desktop_folder_icon:
			no_icons.append('desktop_folder_icon')
		if not cls.my_files_link_icon:
			no_icons.append('my_files_link_icon')
		if not cls.other_links_icon:
			no_icons.append('other_links_icon')
		return cls.get_logon_template(cls.template_paths['main'], str_replacements, no_icons)

	@classmethod
	def generate_shares_shortcuts_snippet(cls, links):
		res = ''
		disabled_share_links = cls.get_disabled_share_links()
		for share, server in links.items():
			disabled_server_links = disabled_share_links.get(server, [])
			if 'all' in disabled_server_links or any(re.match(disabled_link, share) for disabled_link in disabled_server_links):
				continue
			res += 'CreateShareShortcut "{}","{}"\n'.format(server, share)
		return res

	@classmethod
	def generate_teacher_umc_link_snippet(cls, dn):
		with LDAPConnection() as lo:
			try:
				is_teacher = bool(lo.search(base=dn, scope='base', filter=cls.filterTeacher)[0])
			except (ldap.NO_SUCH_OBJECT, IndexError):
				is_teacher = False
			if not is_teacher:
				is_teacher = cls.reTeacher.match(dn)  # old format before migration
		if is_teacher:
			return 'CreateTeacherUmcLink\n'
		return ''

	@classmethod
	def generate_windows_link_script(cls, links, mappings, dn):
		"""
		Create windows user netlogon script.

		:param links: list of tupels which contain link name and link target
		:param mappings:
		:param dn:
		:return: str: a VBS script
		"""
		# create constants and functions
		script = cls.generate_header_and_functions_snippet()

		# create shortcuts to shares
		if cls.create_shortcuts:
			# create folder
			script += 'CreateLinkFolder\n'

			# create custom folder icon
			if cls.desktop_folder_icon:
				script += 'CreateDesktopIcon\n'

			# create My Files link
			if cls.create_myfiles_link:
				script += 'CreateLinkToMyFiles\n'

			# create shortcuts to shares
			# disable individually using ucsschool/userlogon/disabled_share_links/*
			script += cls.generate_shares_shortcuts_snippet(links)

		# create shortcut to umc for teachers
		if cls.create_teacher_umc_link:
			script += cls.generate_teacher_umc_link_snippet(dn)

		# map personal files from c:\users\<uid> to \\server\<uid>
		home_path = cls.get_home_path()
		if cls.create_personal_files_mapping and home_path:
			script += 'SetMyShares "%s"\n' % home_path

		# create drive mappings
		if cls.create_drive_mappings:
			script += cls.generate_drive_mappings_snippet(mappings)

		return script

	def write_windows_link_skripts(self, uid, links, mappings):
		for path in self.get_script_path():
			script = self.generate_windows_link_script(links, mappings, self.dn).replace('\n', '\r\n')
			listener.setuid(0)
			try:
				filepath = os.path.join(path, '{}.vbs'.format(uid))
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
				return frozenset([attributes['gidNumber'][0] for (dn_, attributes,) in res])
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
		with LDAPConnection() as lo:
			if new:
				try:
					if new['uid'][0][-1] == "$":  # machine account
						return
				except:
					pass
				ldapbase = listener.configRegistry['ldap/base']
				membershipIDs = set()

				if new == 'search':  # called from group_change
					try:
						Log.info('got to search %s' % (self.dn,))
						res = lo.search(base=self.dn, scope="base", filter='objectClass=posixAccount')
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
				validservers = frozenset(listener.configRegistry.get(
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

				classShareLetter = listener.configRegistry.get('ucsschool/userlogon/classshareletter', 'K').replace(':', '')
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
				if listener.configRegistry.is_true("ucsschool/userlogon/mac"):
					self.write_mac_link_scripts(new['uid'][0], new['homeDirectory'][0], links)

			elif old and 'posixAccount' in old['objectClass'] and not new:
				listener.setuid(0)
				try:
					for path in self.get_script_path():
						vbs_path = os.path.join(path, '{}.vbs'.format(old['uid'][0]))
						if os.path.exists(vbs_path):
							Log.warn('Deleting netlogon script {}...'.format(vbs_path))
							os.remove(vbs_path)
				finally:
					listener.unsetuid()


def handler(dn, new, old):
	object_class = new.get('objectClass', []) or old.get('objectClass', [])
	script_handler = UserLogonScriptListener(dn, new, old)
	if 'posixAccount' in object_class:
		script_handler.user_change(new, old)
	elif 'univentionShare' in object_class:
		script_handler.share_change()
	elif 'posixGroup' in object_class:
		script_handler.group_change(new, old)
	else:
		raise RuntimeError('Unknown object. objectClass={!r}\n\nold={!r}\n\nnew={!r}'.format(object_class, old, new))


def initialize():
	for path in UserLogonScriptListener.template_paths.values():
		if not os.path.exists(path):
			raise Exception('Missing template file {!r}.'.format(path))


def clean():
	Log.warn('Deleting all netlogon scripts in {!r}...'.format(UserLogonScriptListener.get_script_path()))
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
