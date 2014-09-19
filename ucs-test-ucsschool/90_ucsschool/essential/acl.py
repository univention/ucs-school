# coding=utf-8

"""
.. module:: acl
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""

import copy
import subprocess
from univention.uldap import getMachineConnection
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool as utu
import univention.testing.strings as uts

class FailAcl(Exception):
	pass

class FailCmd(Exception):
	pass

def run_commands(cmdlist, argdict):
	"""
	Start all commands in cmdlist and replace formatstrings with arguments in argdict.\n
	run_commands([['/bin/echo', '%(msg)s'], ['/bin/echo', 'World']], {'msg': 'Hello'})\n
	:return tuple: (output message, error message)
	"""
	result_list = []
	for cmd in cmdlist:
		cmd = copy.deepcopy(cmd)
		for i, val in enumerate(cmd):
			cmd[i] = val % argdict
		print '*** %r' % cmd
		out , err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		result_list.append((out,err))
	return result_list

def create_group_in_container(container_dn):
	"""Create random group in a specific container:\n
	:param container_dn: container dn to create the group in
	:type container_dn: ldap object dn
	"""
	cmd = [
			'udm', 'groups/group', 'create',
			'--position', '%(container)s',
			'--set', 'name=%(group_name)s'
			]
	out , err = run_commands(
			[cmd], {
				'container': container_dn,
				'group_name': uts.random_name()
				}
			)[0]
	if out:
		return out.split(': ')[1].strip()

def create_dc_slave_in_container(container_dn):
	"""Create random computer in a specific container:\n
	:param container_dn: container dn to create the group in
	:type container_dn: ldap object dn
	"""
	cmd = [
			'udm', 'computers/domaincontroller_slave', 'create',
			'--position', '%(container)s',
			'--set', 'name=%(name)s'
			]
	out , err = run_commands(
			[cmd], {
				'container': container_dn,
				'name': uts.random_name(),
				'uidNumber': uts.random_int()
				}
			)[0]
	if out:
		return out.split(': ')[1].strip()

def create_user_in_container(container_dn):
	"""Create random user in a specific container:\n
	:param container_dn: container dn to create the user in
	:type container_dn: ldap object dn
	"""
	cmd = [
			'udm', 'users/user', 'create',
			'--position', '%(container)s',
			'--set', 'username=%(username)s',
			'--set', 'firstname=%(firstname)s',
			'--set','lastname=%(lastname)s',
			'--set', 'password=%(password)s',
			]
	out , err = run_commands([cmd],
			{
				'container': container_dn,
				'username': uts.random_name(),
				'firstname': uts.random_name(),
				'lastname': uts.random_name(),
				'password': uts.random_string(),
				}
			)[0]
	if out:
		return out.split(': ')[1].strip()


class Acl(object):
	"""Acl class\n
	contains the basic functuality to test acls for the common container in ucsschool\n
	may change with time.\n
	"""

	def __init__(self, school, auth_dn, access_allowance):
		"""__init__():\n
		:param school: school name
		:type school: string
		:param auth_dn: dn of the authentication actor
		:type auth_dn: ldap object dn
		:param access_allowance: the expected access result
		:type access_allowance: str: 'ALLOWED' or 'DENIED'
		"""
		self.school = school
		self.auth_dn = auth_dn
		self.access_allowance = access_allowance
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()

	def assert_acl(self, target_dn, access, attrs, access_allowance=None):
		"""Test ACL rule:\n
		:param target_dn: Target dn to test access to
		:type target_dn: ldap object dn
		:param attrs: names of the attributes to test acl against
		:type attrs: list of str
		:param access: type of access
		:type access: str='read' 'write' or 'none'
		"""
		access_allowance = access_allowance if access_allowance else self.access_allowance
		print '\n * Targetdn = %s\n * Authdn = %s\n * Access = %s\n * Access allowance = %s\n' % (
				target_dn, self.auth_dn, access, access_allowance)
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
				result = [x for x in err.split('\n') if ('ALLOWED' in x or 'DENIED' in x)][0]
				if result:
					if access_allowance not in result:
						raise FailAcl('Access (%s) by (%s) to (%s) not expected %r' % (
							access, self.auth_dn, target_dn, result))
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
				'structuralObjectClass',
				'entryUUID',
				'creatorsName',
				'createTimestamp',
				'objectClass',
				'msGPOLink',
				'entryCSN',
				'modifiersName',
				'modifyTimestamp',
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
		target_dn = 'cn=raeume,cn=groups,%s' % utu.UCSTestSchool().get_ou_base_dn(self.school)
		attrs = [
				'children',
				'entry',
				]
		self.assert_acl(target_dn, access, attrs)
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
				'structuralObjectClass',
				'entryUUID',
				'creatorsName',
				'createTimestamp',
				'entryCSN',
				'modifiersName',
				'modifyTimestamp',
				]
		self.assert_acl(room_dn, access, attrs)
		target_dn = create_dc_slave_in_container(target_dn)
		self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

	def assert_teacher_group(self, access):
		"""Lehrer, Mitarbeiter und Mitglieder der lokalen Administratoren
		duerfen Arbeitsgruppen anlegen und aendern
		"""
		group_dn = 'cn=lehrer,cn=groups,%s' % utu.UCSTestSchool().get_ou_base_dn(self.school)
		attrs = [
				'children',
				'entry',
				]
		self.assert_acl(group_dn, access, attrs)
		target_dn = create_dc_slave_in_container(group_dn)
		self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')
		group_dn = create_group_in_container(group_dn)
		# access to dn.regex="^cn=([^,]+),(cn=lehrer,|cn=schueler,|)cn=groups,ou=([^,]+),dc=najjar,dc=am$$"
		# filter="(&(!(|(uidNumber=*)(objectClass=SambaSamAccount)))(objectClass=univentionGroup))"
		attrs = [
				'sambaGroupType',
				'cn',
				'description',
				'objectClass',
				'objectClass',
				'objectClass',
				'objectClass',
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
		group_dn = 'cn=schueler,cn=groups,%s' % utu.UCSTestSchool().get_ou_base_dn(self.school)
		attrs = [
				'children',
				'entry',
				]
		self.assert_acl(group_dn, access, attrs)

		target_dn = create_dc_slave_in_container(group_dn)
		self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')
		group_dn = create_group_in_container(group_dn)
		attrs = [
				'sambaGroupType',
				'cn',
				'description',
				'objectClass',
				'objectClass',
				'objectClass',
				'objectClass',
				'objectClass',
				'memberUid',
				'univentionObjectType',
				'gidNumber',
				'sambaSID',
				'uniqueMember',
				'univentionGroupType',
				]
		self.assert_acl(group_dn, access, attrs)

	def assert_shares(self, shares_dn, access):
		"""Lehrer und Mitglieder der lokalen Administratoren duerfen Shares anlegen,
		Klassenshares aber nicht aendern
		"""
		attrs = [
				'children',
				'entry',
				]
		self.assert_acl(shares_dn, access, attrs)
		target_dn = create_dc_slave_in_container(shares_dn)
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
		target_dn = create_dc_slave_in_container(temp_dn)
		self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')
		temp_dn = 'cn=mac,cn=temporary,cn=univention,%s' % base_dn
		self.assert_acl(temp_dn, access, attrs)
		target_dn = create_dc_slave_in_container(temp_dn)
		self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')
		temp_dn = 'cn=groupName,cn=temporary,cn=univention,%s' % base_dn
		self.assert_acl(temp_dn, access, attrs)
		target_dn = create_dc_slave_in_container(temp_dn)
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
		target_dn = create_dc_slave_in_container(temp_dn)
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
			'structuralObjectClass',
			'entryUUID',
			'creatorsName',
			'createTimestamp',
			'ucsschoolHomeShareFileServer',
			'ucsschoolClassShareFileServer',
			'univentionPolicyReference',
			'objectClass',
			'entryCSN',
			'modifiersName',
			'modifyTimestamp',
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
			'structuralObjectClass',
			'entryUUID',
			'creatorsName',
			'createTimestamp',
			'entryCSN',
			'modifiersName',
			'modifyTimestamp',
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
				'sambaNTPassword'
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

	def assert_dhcp(self, client, access):
		client_dhcp_dn = 'cn=%s,cn=%s,cn=dhcp,%s' % (
				client, self.school, utu.UCSTestSchool().get_ou_base_dn(self.school))
		attrs = [
				'entry',
				'children',
				'objectClass',
				'univentionObjectType',
				'dhcpOption',
				'cn',
				'structuralObjectClass',
				'entryUUID',
				'creatorsName',
				'createTimestamp',
				'entryCSN',
				'modifiersName',
				'modifyTimestamp',
				]
		self.assert_acl(client_dhcp_dn, access, attrs)
		target_dn = create_dc_slave_in_container(client_dhcp_dn)
		self.assert_acl(target_dn, access, attrs, access_allowance='DENIED')

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
			slave_found= lo.search(filter="(|(univentionObjectType=computers/domaincontroller_slave)(univentionObjectType=computers/memberserver))", base=utu.UCSTestSchool().get_ou_base_dn(self.school))
			if slave_found:
				slave_dn = slave_found[0][0]
				self.assert_acl(slave_dn, access, attrs)

		attrs = ['sOARecord']
		zoneName = lo.search(base='cn=dns,%s' % base_dn, scope='base+one',attr=['uid'])
		for (target_dn, d) in zoneName:
			if 'zoneName' in target_dn:
				self.assert_acl(target_dn, access, attrs)
				break
