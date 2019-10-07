# coding=utf-8

"""
.. module:: acl
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from __future__ import print_function

import copy
import subprocess
from univention.uldap import getMachineConnection
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.strings as uts
import univention.testing.udm as udm_test



class FailAcl(Exception):
	pass


class FailCmd(Exception):
	pass


def run_commands(cmdlist, argdict):
	"""
	Start all commands in cmdlist and replace formatstrings with arguments in argdict.

	>>> run_commands([['/bin/echo', '%(msg)s'], ['/bin/echo', 'World']], {'msg': 'Hello'})
	[('Hello\n', ''), ('World\n', '')]

	:param list cmdlist: list of commands to start
	:param dict argdict: formatstrings for commands in `cmdlist`
	:return: tuple: (output message, error message)
	:rtype: tuple[str, str]
	"""
	result_list = []
	for cmd in cmdlist:
		cmd = copy.deepcopy(cmd)
		for i, val in enumerate(cmd):
			cmd[i] = val % argdict
		print('*** %r' % cmd)
		out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		result_list.append((out, err))
	return result_list


class CreateContextManager(object):
	udm_module = ''
	create_kwargs = {}

	def __init__(self, container_dn, **kwargs):
		"""
		Create random object in a specific container:

		:param str container_dn: container dn to create the object in
		:param kwargs: arguments to pass to `udm.create_object()` additionally to cls.create_kwargs
		"""
		self.container_dn = container_dn
		self.create_kwargs.update(kwargs)
		self.udm = None
		self.dn = ''

	def __enter__(self):
		self.udm = udm_test.UCSTestUDM()
		self.dn = self.udm.create_object(self.udm_module, position=self.container_dn, **self.create_kwargs)
		return self.dn

	def __exit__(self, exc_type, exc_value, etraceback):
		if exc_type:
			print('*** Cleanup after exception: %s %s' % (exc_type, exc_value))
		self.udm.cleanup()


class CreateGroupInContainer(CreateContextManager):
	udm_module = 'groups/group'
	create_kwargs = {'name': uts.random_name()}


class CreateDCSlaveInContainer(CreateContextManager):
	udm_module = 'computers/domaincontroller_slave'
	create_kwargs = {'name': uts.random_name()}


class Acl(object):
	"""
	Acl class

	contains the basic functuality to test acls for the common container in
	ucsschool may change with time.
	"""

	def __init__(self, school, auth_dn, access_allowance):
		"""
		:param str school: school name
		:param str auth_dn: dn of the authentication actor
		:param str access_allowance: the expected access result - `ALLOWED` or `DENIED`
		"""
		self.school = school
		self.auth_dn = auth_dn
		self.access_allowance = access_allowance
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()

	def assert_acl(self, target_dn, access, attrs, access_allowance=None):
		"""
		Test ACL rule:

		:param str target_dn: Target dn to test access to
		:param  attrs: names of the attributes to test acl against
		:type attrs: list[str]
		:param str access: type of access - `read`, `write` or `none`
		"""
		access_allowance = access_allowance if access_allowance else self.access_allowance
		print('\n * Targetdn = %s\n * Authdn = %s\n * Access = %s\n * Access allowance = %s\n' % (target_dn, self.auth_dn, access, access_allowance))
		cmd = [
			'slapacl',
			'-f',
			'/etc/ldap/slapd.conf',
			'-D',
			'%(self.auth_dn)s',
			'-b',
			'%(target_dn)s',
			'%(attr)s/%(access)s',
			'-d',
			'0'
		]
		for attr in attrs:
			argdict = {'self.auth_dn': self.auth_dn, 'target_dn': target_dn, 'access': access, 'attr': attr}
			out, err = run_commands([cmd], argdict)[0]
			if err:
				try:
					result = [x for x in err.split('\n') if ('ALLOWED' in x or 'DENIED' in x)][0]
				except IndexError:
					result = None
					print('Failed to parse slapacl output:', attr, err)
				if result and access_allowance not in result:
					raise FailAcl('Access (%s) by (%s) to (%s) not expected %r' % (access, self.auth_dn, target_dn, result))
			else:
				raise FailCmd('command %r was not executed successfully' % cmd)

	def assert_base_dn(self, access):
		"""General acces rule = all read"""
		base_dn = self.ucr.get('ldap/base')
		attrs = [
			'entry',
			'children',
			'dc',
			'univentionObjectType',
			'krb5RealmName',
			'nisDomain',
			'associatedDomain',
			'univentionPolicyReference',
			'msGPOLink',
		]
		self.assert_acl(base_dn, access, attrs)

	def assert_student(self, stu_dn, access):
		"""Lehrer, Mitarbeiter und OU-Admins duerfen Schueler-Passwoerter aendern
		"""
		attrs = [
			'krb5KeyVersionNumber',
			'krb5KDCFlags',
			'krb5Key',
			'krb5PasswordEnd',
			'sambaAcctFlags',
			'sambaPwdLastSet',
			'sambaLMPassword',
			'sambaNTPassword',
			'shadowLastChange',
			'shadowMax',
			'userPassword',
			'pwhistory',
			'sambaPwdCanChange',
			'sambaPwdMustChange',
			'sambaPasswordHistory',
			'sambaBadPasswordCount'
		]
		self.assert_acl(stu_dn, access, attrs)

	def assert_room(self, room_dn, access):
		"""Lehrer und ouadmins duerfen Raum-Gruppen anlegen und bearbeiten
		"""
		container_dn = 'cn=raeume,cn=groups,%s' % utu.UCSTestSchool().get_ou_base_dn(self.school)
		attrs = [
			'children',
			'entry',
		]
		self.assert_acl(container_dn, access, attrs)
		# access to dn.regex="^cn=([^,]+),cn=raeume,cn=groups,ou=([^,]+),dc=najjar,dc=am$$"
		# filter="(&(!(|(uidNumber=*)(objectClass=SambaSamAccount)))(objectClass=univentionGroup))"
		attrs = [
			'entry',
			'children',
			'sambaGroupType',
			'cn',
			'objectClass',
			'univentionObjectType',
			'gidNumber',
			'sambaSID',
			'univentionGroupType',
		]
		self.assert_acl(room_dn, access, attrs)
		with CreateDCSlaveInContainer(container_dn) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

	def assert_teacher_group(self, access):
		"""Lehrer, Mitarbeiter und Mitglieder der lokalen Administratoren
		duerfen Arbeitsgruppen anlegen und aendern
		"""
		group_container = 'cn=lehrer,cn=groups,%s' % utu.UCSTestSchool().get_ou_base_dn(self.school)
		attrs = [
			'children',
			'entry',
		]
		self.assert_acl(group_container, access, attrs)
		with CreateDCSlaveInContainer(group_container) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')
			with CreateGroupInContainer(group_container) as group_dn:
				# access to dn.regex="^cn=([^,]+),(cn=lehrer,|cn=schueler,|)cn=groups,ou=([^,]+),dc=najjar,dc=am$$"
				# filter="(&(!(|(uidNumber=*)(objectClass=SambaSamAccount)))(objectClass=univentionGroup))"
				attrs = [
					'sambaGroupType',
					'cn',
					'description',
					'objectClass',
					'memberUid',
					'univentionObjectType',
					'gidNumber',
					'sambaSID',
					'uniqueMember',
					'univentionGroupType',
				]
				self.assert_acl(group_dn, access, attrs)

	def assert_student_group(self, access):
		group_container = 'cn=schueler,cn=groups,%s' % utu.UCSTestSchool().get_ou_base_dn(self.school)
		attrs = [
			'children',
			'entry',
		]
		self.assert_acl(group_container, access, attrs)

		with CreateDCSlaveInContainer(group_container) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')
			with CreateGroupInContainer(group_container) as group_dn:
				attrs = [
					'sambaGroupType',
					'cn',
					'description',
					'objectClass',
					'memberUid',
					'univentionObjectType',
					'gidNumber',
					'sambaSID',
					'uniqueMember',
					'univentionGroupType',
				]
				self.assert_acl(group_dn, access, attrs)

	def assert_share_object_access(self, share_dn, access, access_allowance='ALLOWED'):
		"""
		Assert that for the given share object the given <access>, "read" or "write", is (not) given.
		Please note that the attribute list may not be complete.
		"""
		share_attribute_list = [
			'univentionShareNFSSync',
			'univentionShareSambaForceDirectoryMode',
			'cn',
			'objectClass',
			'univentionShareSambaDosFilemode',
			'univentionShareSambaForceSecurityMode',
			'univentionShareSambaLocking',
			'univentionShareSambaForceDirectorySecurityMode',
			'univentionShareSambaMSDFS',
			'univentionShareSambaCreateMode',
			'univentionShareSambaWriteable',
			'univentionShareSambaInheritPermissions',
			'univentionShareSambaBrowseable',
			'univentionShareSambaHideUnreadable',
			'univentionShareSambaInheritAcls',
			'univentionShareSambaPublic',
			'univentionShareSambaSecurityMode',
			'univentionShareDirectoryMode',
			'univentionShareSambaBlockingLocks',
			'univentionSharePath',
			'univentionShareWriteable',
			'univentionShareSambaDirectorySecurityMode',
			'univentionShareSambaLevel2Oplocks',
			'univentionShareSambaNtAclSupport',
			'univentionShareSambaCscPolicy',
			'univentionShareSambaForceCreateMode',
			'univentionObjectType',
			'univentionShareSambaOplocks',
			'univentionShareSambaDirectoryMode',
			'univentionShareSambaForceGroup',
			'univentionShareSambaFakeOplocks',
			'univentionShareGid',
			'univentionShareNFSRootSquash',
			'univentionShareUid',
			'univentionShareSambaStrictLocking',
			'univentionShareSambaName',
			'univentionShareNFSSubTree',
			'univentionShareSambaInheritOwner',
			'univentionShareHost',
		]
		self.assert_acl(share_dn, access, share_attribute_list, access_allowance)

	def assert_shares(self, shares_dn, access):
		"""Lehrer und Mitglieder der lokalen Administratoren duerfen Shares anlegen,
		Klassenshares aber nicht aendern
		"""
		attrs = [
			'children',
			'entry',
		]
		self.assert_acl(shares_dn, access, attrs)
		with CreateDCSlaveInContainer(shares_dn) as target_dn:
			self.assert_acl(target_dn, 'write', attrs, access_allowance='DENIED')

	def assert_temps(self, access):
		"""Mitglieder der lokalen Administratoren muessen einige temporaere
		Objekte schreiben duerfen da keine regulaeren Ausdruecke auf
		Gruppenmitgliedschaften moeglich sind wird dies allen Lehrern erlaubt
		"""
		base_dn = self.ucr.get('ldap/base')
		temp_dn = 'cn=sid,cn=temporary,cn=univention,%s' % base_dn
		attrs = [
			'children',
			'entry',
		]
		self.assert_acl(temp_dn, access, attrs)

		temp_dn = 'cn=gid,cn=temporary,cn=univention,%s' % base_dn
		self.assert_acl(temp_dn, access, attrs)
		with CreateDCSlaveInContainer(temp_dn) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

		temp_dn = 'cn=mac,cn=temporary,cn=univention,%s' % base_dn
		self.assert_acl(temp_dn, access, attrs)
		with CreateDCSlaveInContainer(temp_dn) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

		temp_dn = 'cn=groupName,cn=temporary,cn=univention,%s' % base_dn
		self.assert_acl(temp_dn, access, attrs)
		with CreateDCSlaveInContainer(temp_dn) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

	def assert_gid_temps(self, access):
		base_dn = self.ucr.get('ldap/base')
		temp_dn = 'cn=gidNumber,cn=temporary,cn=univention,%s' % base_dn
		attrs = [
			'children',
			'entry',
			'univentionLastUsedValue'
		]
		self.assert_acl(temp_dn, access, attrs)
		with CreateDCSlaveInContainer(temp_dn) as target_dn:
			self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

	def assert_ou(self, access):
		"""Slave-Controller duerfen Eintraege Ihrer ou lesen und schreiben
		(Passwortaenderungen etc.)
		Lehrer und Memberserver duerfen sie lesen, ou-eigene bekommen
		Standard-ACLs, ou-fremde Server/user duerfen nichts
		"""
		attrs = [
			'entry',
			'children',
			'ou',
			'displayName',
			'univentionObjectType',
			'ucsschoolHomeShareFileServer',
			'ucsschoolClassShareFileServer',
			'univentionPolicyReference',
			'objectClass',
		]
		target_dn = utu.UCSTestSchool().get_ou_base_dn(self.school)
		self.assert_acl(target_dn, access, attrs)

	def assert_global_containers(self, access):
		"""Schüler, Lehrer, Mitarbeiter, Admins duerfen globale Container univention,
		policies, groups und dns lesen (werden bei Schuelern/Rechnern angezeigt)
		"""
		base_dn = self.ucr.get('ldap/base')
		attrs = [
			'entry',
			'children',
			'objectClass',
			'univentionObjectType',
			'description',
			'cn',
		]
		container_dn = 'cn=univention,%s' % base_dn
		self.assert_acl(container_dn, access, attrs)
		container_dn = 'cn=dns,%s' % base_dn
		self.assert_acl(container_dn, access, attrs)
		container_dn = 'cn=policies,%s' % base_dn
		self.assert_acl(container_dn, access, attrs)
		container_dn = 'cn=groups,%s' % base_dn
		self.assert_acl(container_dn, access, attrs)

	def assert_computers(self, computer_dn, access):
		"""Mitglieder der lokalen Administratoren duerfen MAC-Adressen
		im Rechner- und DHCP-Objekt aendern
		"""
		attrs = [
			'macAddress',
		]
		self.assert_acl(computer_dn, access, attrs)

	def assert_user(self, user_dn, access):
		"""Mitglieder der lokalen Administratoren duerfen Passwoerter unterhalb
		von cn=users aendern
		"""
		attrs = [
			'krb5KeyVersionNumber',
			'krb5KDCFlags',
			'krb5Key',
			'krb5PasswordEnd',
			'sambaAcctFlags',
			'sambaPwdLastSet',
			'sambaLMPassword',
			'sambaNTPassword',
			'shadowLastChange',
			'shadowMax',
			'userPassword',
			'pwhistory',
			'sambaPwdCanChange',
			'sambaPwdMustChange',
			'sambaPasswordHistory',
			'sambaBadPasswordCount'
		]
		self.assert_acl(user_dn, access, attrs)

	def assert_dhcp(self, client, access, modify_only_attrs=False):
		"""
		Check access to DHCP host objects.
		By default, all attributes are checked. If modify_only_attrs is True,
		only attributes that are required to modify the DHCP host object are
		checked.
		"""
		client_dhcp_dn = 'cn=%s,cn=%s,cn=dhcp,%s' % (client, self.school, utu.UCSTestSchool().get_ou_base_dn(self.school))
		attrs = [
			'entry',
			'children',
			'dhcpOption',
		]
		if not modify_only_attrs:
			attrs += [
				'objectClass',
				'univentionObjectType',
				'cn',
			]
		self.assert_acl(client_dhcp_dn, access, attrs)

	def assert_member_server(self, access):
		"""Mitglieder der lokalen Administratoren duerfen den DC-Slave und Memberserver
		joinen (benoetigt Passwortaenderung)
		"""
		base_dn = self.ucr.get('ldap/base')
		attrs = [
			'krb5KeyVersionNumber',
			'krb5KDCFlags',
			'krb5Key',
			'krb5PasswordEnd',
			'sambaAcctFlags',
			'sambaPwdLastSet',
			'sambaLMPassword',
			'sambaNTPassword',
			'shadowLastChange',
			'shadowMax',
			'userPassword',
			'pwhistory',
			'sambaPwdCanChange',
			'sambaPwdMustChange',
			'sambaPasswordHistory',
		]
		singlemaster = self.ucr.is_true('ucsschool/singlemaster')
		lo = getMachineConnection()
		if not singlemaster:
			slave_found = lo.search(filter="(|(univentionObjectType=computers/domaincontroller_slave)(univentionObjectType=computers/memberserver))", base=utu.UCSTestSchool().get_ou_base_dn(self.school))
			if slave_found:
				slave_dn = slave_found[0][0]
				self.assert_acl(slave_dn, access, attrs)

		attrs = ['sOARecord']
		zoneName = lo.search(base='cn=dns,%s' % base_dn, scope='base+one', attr=['uid'])
		for (target_dn, d) in zoneName:
			if 'zoneName' in target_dn:
				self.assert_acl(target_dn, access, attrs)
				break
