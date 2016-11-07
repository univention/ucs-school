"""
.. module:: School
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from essential.importcomputers import random_ip
from essential.importou import DCNotFound, DCMembership, DhcpdLDAPBase, TYPE_DC_ADMINISTRATIVE
from essential.importou import get_ou_base, verify_dc, get_school_ou_from_dn, TYPE_DC_EDUCATIONAL
from univention.testing.ucsschool import UMCConnection
from univention.testing.ucsschool import UCSTestSchool
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils
import univention.uldap


class GetFail(Exception):
	pass


class GetCheckFail(Exception):
	pass


class CreateFail(Exception):
	pass


class QueryCheckFail(Exception):
	pass


class RemoveFail(Exception):
	pass


class EditFail(Exception):
	pass


def create_dc_slave(udm, school=None):
	with ucr_test.UCSTestConfigRegistry() as ucr:
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.binddn
		passwd = account.bindpw
		ldap_base = ucr.get('ldap/base')
		ip = random_ip()
		name = uts.random_name()

		def dns_forward():
			return 'zoneName=%s,cn=dns,%s' % (ucr.get('domainname'), ucr.get('ldap/base'))

		def dns_reverse(ip):
			return 'zoneName=%s.in-addr.arpa,cn=dns,%s' % ('.'.join(reversed(ip.split('.')[:3])), ucr.get('ldap/base'))

		print 'Creating DC Slave (%s)' % name
		position = 'cn=dc,cn=computers,%s' % ldap_base
		if not ucr.is_true('ucsschool/singlemaster', False):
			position = 'cn=dc,cn=server,cn=computers,ou=%s,%s' % (school, ldap_base)
		dn = udm.create_object(
			'computers/domaincontroller_slave',
			binddn=admin,
			bindpwd=passwd,
			position=position,
			ip=ip,
			name=name,
			options=[
				"samba=True",
				"kerberos=True",
				"posix=True",
				"nagios=False",
			]
		)
		if dn:
			return name, dn
		else:
			utils.fail('Could not create a DC Slave via udm')


class School(object):

	"""Contains the needed functuality for schools in the UMC module schoolwizards/schools.
	By default they are randomly formed.\n
	:param umcConnection:
	:type umcConnection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	:param name: name of the school to be created later
	:type name: str
	:param display_name: display_name of the school to be created later
	:type display_name: str
	"""

	# Initialization (Random by default)

	def __init__(self, display_name=None, name=None, dc_name=None, ucr=None, umcConnection=None):
		self.class_share_file_server = None
		self.home_share_file_server = None
		self.name = name if name else uts.random_string()
		self.display_name = display_name if display_name else uts.random_string()
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		singlemaster = self.ucr.is_true('ucsschool/singlemaster')
		if singlemaster:
			self.dc_name = None
		else:
			self.dc_name = dc_name if dc_name else uts.random_string()
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr = ucr_test.UCSTestConfigRegistry()
			self.ucr.load()
			host = self.ucr.get('ldap/master')
			self.umcConnection = UMCConnection(host)
			account = utils.UCSTestDomainAdminCredentials()
			admin = account.username
			passwd = account.bindpw
			self.umcConnection.auth(admin, passwd)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def create(self):
		"""Creates object school"""
		flavor = 'schoolwizards/schools'
		param = [{
			'object': {
				'name': self.name,
				'dc_name': self.dc_name,
				'display_name': self.display_name,
			},
			'options': None
		}]
		print 'Creating school %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/add',
				param,
				flavor)
		if reqResult[0] is not True:
			raise CreateFail('Unable to create school (%r)' % (reqResult,))
		else:
			utils.wait_for_replication()

	def get(self):
		"""get the list of existing schools in the school"""
		flavor = 'schoolwizards/schools'
		param = [{'object': {
			'$dn$': self.dn()
		}}]
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/get', param, flavor)
		return reqResult

	def check_get(self, attrs):
		current_attrs = self.get()[0]
		expected = dict(current_attrs)
		expected.update(attrs)
		if current_attrs != expected:
			raise GetCheckFail('Attributes do not match,\nfound (%r)\nexpected (%r)' % (
				current_attrs, expected))

	def query(self):
		"""get the list of existing schools in the school"""
		flavor = 'schoolwizards/schools'
		param = {
			'school': 'undefined',
			'filter': ""
		}
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/query', param, flavor)
		return reqResult

	def check_query(self, names):
		q = self.query()
		k = [x['name'] for x in q]
		if not set(names).issubset(set(k)):
			raise QueryCheckFail('schools from query do not contain the existing schools, found (%r), expected (%r)' % (
				k, names))

	def dn(self):
		return UCSTestSchool().get_ou_base_dn(self.name)

	def remove(self):
		"""Remove school"""
		print 'Removing school: %s' % self.name
		flavor = 'schoolwizards/schools'
		param = [{
			'object': {
				'$dn$': self.dn(),
			},
			'options': None
		}]
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/remove', param, flavor)
		if not reqResult[0]:
			raise RemoveFail('Unable to remove school (%s)' % self.name)
		else:
			utils.wait_for_replication()

	def edit(self, new_attributes):
		"""Edit object school"""
		flavor = 'schoolwizards/schools'
		if self.dc_name:
			host = self.dc_name
			if new_attributes.get('home_share_file_server'):
				host = new_attributes['home_share_file_server']
			home_share = 'cn=%s,cn=dc,cn=server,cn=computers,%s' % (
					host, UCSTestSchool().get_ou_base_dn(self.name))

			host = self.dc_name
			if new_attributes.get('class_share_file_server'):
				host = new_attributes['class_share_file_server']
			class_share = 'cn=%s,cn=dc,cn=server,cn=computers,%s' % (
					host, UCSTestSchool().get_ou_base_dn(self.name))
		else:
			host = self.ucr.get('hostname')
			if new_attributes.get('home_share_file_server'):
				host = new_attributes['home_share_file_server']
			home_share = 'cn=%s,cn=dc,cn=computers,%s' % (
					host, self.ucr.get('ldap/base'))

			host = self.ucr.get('hostname')
			if new_attributes.get('class_share_file_server'):
				host = new_attributes['class_share_file_server']
			class_share = 'cn=%s,cn=dc,cn=computers,%s' % (
					host, self.ucr.get('ldap/base'))
		param = [{
			'object': {
				'$dn$': self.dn(),
				'name': self.name,
				'home_share_file_server': home_share,
				'class_share_file_server': class_share,
				'dc_name': self.dc_name,
				'display_name': new_attributes['display_name']
			},
			'options': None
		}]
		print 'Editing school %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/put',
				param,
				flavor)
		if not reqResult[0]:
			raise EditFail('Unable to edit school (%s) with the parameters (%r)' % (self.name, param))
		else:
			self.home_share_file_server = home_share
			self.class_share_file_server = class_share
			self.display_name = new_attributes['display_name']
			utils.wait_for_replication()

	def verify_ldap(self, should_exist):
		homeshare = ''
		classshare = ''
		if self.home_share_file_server:
			homeshare = self.home_share_file_server[3:].split(',')[0]
		if self.class_share_file_server:
			classshare = self.class_share_file_server[3:].split(',')[0]
		self.verify_ou(self.name, self.dc_name, self.ucr, homeshare, classshare, None, should_exist)

	def verify_ou(self, ou, dc, ucr, homesharefileserver, classsharefileserver, dc_administrative, must_exist):
		print '*** Verifying OU (%s) ... ' % ou
		ucr.load()

		dc_name = ucr.get('hostname')
		old_dhcpd_ldap_base = ucr.get('dhcpd/ldap/base')
		lo = univention.uldap.getMachineConnection()
		base_dn = ucr.get('ldap/base')

		cn_pupils = ucr.get('ucsschool/ldap/default/container/pupils', 'schueler')
		cn_teachers = ucr.get('ucsschool/ldap/default/container/teachers', 'lehrer')
		cn_teachers_staff = ucr.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
		cn_admins = ucr.get('ucsschool/ldap/default/container/admins', 'admins')
		cn_staff = ucr.get('ucsschool/ldap/default/container/staff', 'mitarbeiter')

		singlemaster = ucr.is_true('ucsschool/singlemaster')
		noneducational_create_objects = ucr.is_true('ucsschool/ldap/noneducational/create/objects')
		district_enable = ucr.is_true('ucsschool/ldap/district/enable')
		# default_dcs = ucr.get('ucsschool/ldap/default/dcs')
		dhcp_dns_clearou = ucr.is_true('ucsschool/import/generate/policy/dhcp/dns/clearou')
		ou_base = get_ou_base(ou, district_enable)

		# does dc exist?
		if singlemaster:
			dc_dn = ucr.get('ldap/hostdn')
			dc_name = ucr.get('hostname')
		elif dc:
			dc_dn = 'cn=%s,cn=dc,cn=server,cn=computers,%s' % (dc, ou_base)
			dc_name = dc
		else:
			dc_dn = 'cn=dc%s-01,cn=dc,cn=server,cn=computers,%s' % (ou, ou_base)
			dc_name = 'dc%s-01' % ou

		homesharefileserver_dn = dc_dn
		if homesharefileserver:
			result = lo.search(filter='(&(objectClass=univentionDomainController)(cn=%s))' % homesharefileserver, base=base_dn, attr=['cn'])
			if result:
				homesharefileserver_dn = result[0][0]

		classsharefileserver_dn = dc_dn
		if classsharefileserver:
			result = lo.search(filter='(&(objectClass=univentionDomainController)(cn=%s))' % classsharefileserver, base=base_dn, attr=['cn'])
			if result:
				classsharefileserver_dn = result[0][0]

		utils.verify_ldap_object(ou_base, expected_attr={'ou': [ou], 'ucsschoolClassShareFileServer': [classsharefileserver_dn], 'ucsschoolHomeShareFileServer': [homesharefileserver_dn]}, should_exist=must_exist)

		utils.verify_ldap_object('cn=printers,%s' % ou_base, expected_attr={'cn': ['printers']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=users,%s' % ou_base, expected_attr={'cn': ['users']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_pupils, ou_base), expected_attr={'cn': [cn_pupils]}, should_exist=must_exist)
		utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_teachers, ou_base), expected_attr={'cn': [cn_teachers]}, should_exist=must_exist)
		utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_admins, ou_base), expected_attr={'cn': [cn_admins]}, should_exist=must_exist)
		utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_admins, ou_base), expected_attr={'cn': [cn_admins]}, should_exist=must_exist)

		utils.verify_ldap_object('cn=computers,%s' % ou_base, expected_attr={'cn': ['computers']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=server,cn=computers,%s' % ou_base, expected_attr={'cn': ['server']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=dc,cn=server,cn=computers,%s' % ou_base, expected_attr={'cn': ['dc']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=networks,%s' % ou_base, expected_attr={'cn': ['networks']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=groups,%s' % ou_base, expected_attr={'cn': ['groups']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=%s,cn=groups,%s' % (cn_pupils, ou_base), expected_attr={'cn': [cn_pupils]}, should_exist=must_exist)
		utils.verify_ldap_object('cn=%s,cn=groups,%s' % (cn_teachers, ou_base), expected_attr={'cn': [cn_teachers]}, should_exist=must_exist)
		utils.verify_ldap_object('cn=klassen,cn=%s,cn=groups,%s' % (cn_pupils, ou_base), expected_attr={'cn': ['klassen']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=raeume,cn=groups,%s' % ou_base, expected_attr={'cn': ['raeume']}, should_exist=must_exist)

		utils.verify_ldap_object('cn=dhcp,%s' % ou_base, expected_attr={'cn': ['dhcp']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=policies,%s' % ou_base, expected_attr={'cn': ['policies']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=shares,%s' % ou_base, expected_attr={'cn': ['shares']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=klassen,cn=shares,%s' % ou_base, expected_attr={'cn': ['klassen']}, should_exist=must_exist)
		utils.verify_ldap_object('cn=dc,cn=server,cn=computers,%s' % ou_base, expected_attr={'cn': ['dc']}, should_exist=must_exist)

		if noneducational_create_objects:
			utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_staff, ou_base), should_exist=must_exist)
			utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_teachers_staff, ou_base), should_exist=must_exist)
			utils.verify_ldap_object('cn=%s,cn=groups,%s' % (cn_staff, ou_base), should_exist=must_exist)
		else:
			utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_staff, ou_base), should_exist=False)
			utils.verify_ldap_object('cn=%s,cn=users,%s' % (cn_teachers_staff, ou_base), should_exist=False)
			utils.verify_ldap_object('cn=%s,cn=groups,%s' % (cn_staff, ou_base), should_exist=False)

		if noneducational_create_objects:
			utils.verify_ldap_object('cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % base_dn, should_exist=True)
			utils.verify_ldap_object('cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % base_dn, should_exist=True)
			utils.verify_ldap_object('cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (ou, base_dn), should_exist=True)
			utils.verify_ldap_object('cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (ou, base_dn), should_exist=True)
		# This will fail because we don't cleanup these groups in cleanup_ou
		#else:
		#	utils.verify_ldap_object("cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn, should_exist=False)
		#	utils.verify_ldap_object("cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn, should_exist=False)
		#	utils.verify_ldap_object('cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (ou, base_dn), should_exist=False)
		#	utils.verify_ldap_object('cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (ou, base_dn), should_exist=False)

		if not singlemaster:
			verify_dc(ou, dc_name, TYPE_DC_EDUCATIONAL, base_dn, must_exist)

		if dc_administrative:
			verify_dc(ou, dc_administrative, TYPE_DC_ADMINISTRATIVE, base_dn, must_exist)

		grp_prefix_pupils = ucr.get('ucsschool/ldap/default/groupprefix/pupils', 'schueler-')
		grp_prefix_teachers = ucr.get('ucsschool/ldap/default/groupprefix/teachers', 'lehrer-')
		grp_prefix_admins = ucr.get('ucsschool/ldap/default/groupprefix/admins', 'admins-')
		grp_prefix_staff = ucr.get('ucsschool/ldap/default/groupprefix/staff', 'mitarbeiter-')

		grp_policy_pupils = ucr.get('ucsschool/ldap/default/policy/umc/pupils', 'cn=ucsschool-umc-pupils-default,cn=UMC,cn=policies,%s' % base_dn)
		grp_policy_teachers = ucr.get('ucsschool/ldap/default/policy/umc/teachers', 'cn=ucsschool-umc-teachers-default,cn=UMC,cn=policies,%s' % base_dn)
		grp_policy_admins = ucr.get('ucsschool/ldap/default/policy/umc/admins', 'cn=ucsschool-umc-admins-default,cn=UMC,cn=policies,%s' % base_dn)
		grp_policy_staff = ucr.get('ucsschool/ldap/default/policy/umc/staff', 'cn=ucsschool-umc-staff-default,cn=UMC,cn=policies,%s' % base_dn)

		utils.verify_ldap_object("cn=%s%s,cn=ouadmins,cn=groups,%s" % (grp_prefix_admins, ou, base_dn), expected_attr={'univentionPolicyReference': [grp_policy_admins]}, should_exist=True)
		utils.verify_ldap_object("cn=%s%s,cn=groups,%s" % (grp_prefix_pupils, ou, ou_base), expected_attr={'univentionPolicyReference': [grp_policy_pupils]}, should_exist=must_exist)
		utils.verify_ldap_object("cn=%s%s,cn=groups,%s" % (grp_prefix_teachers, ou, ou_base), expected_attr={'univentionPolicyReference': [grp_policy_teachers]}, should_exist=must_exist)

		if noneducational_create_objects:
			utils.verify_ldap_object("cn=%s%s,cn=groups,%s" % (grp_prefix_staff, ou, ou_base), expected_attr={'univentionPolicyReference': [grp_policy_staff]}, should_exist=must_exist)

		dcmaster_module = univention.admin.modules.get("computers/domaincontroller_master")
		dcbackup_module = univention.admin.modules.get("computers/domaincontroller_backup")
		dcslave_module = univention.admin.modules.get("computers/domaincontroller_slave")

		masterobjs = univention.admin.modules.lookup(dcmaster_module, None, lo, scope='sub', superordinate=None, base=base_dn,
												filter=univention.admin.filter.expression('cn', dc_name))
		backupobjs = univention.admin.modules.lookup(dcbackup_module, None, lo, scope='sub', superordinate=None, base=base_dn,
												filter=univention.admin.filter.expression('cn', dc_name))
		slaveobjs = univention.admin.modules.lookup(dcslave_module, None, lo, scope='sub', superordinate=None, base=base_dn,
												filter=univention.admin.filter.expression('cn', dc_name))

		# check group membership
		#  slave should be member
		#  master and backup should not be member
		dcgroups = ["cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn),
					"cn=DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (base_dn)]

		if must_exist:
			if masterobjs:
				is_master_or_backup = True
				dcobject = masterobjs[0]
			elif backupobjs:
				is_master_or_backup = True
				dcobject = backupobjs[0]
			elif slaveobjs:
				is_master_or_backup = False
				dcobject = slaveobjs[0]
			else:
				raise DCNotFound()

			dcobject.open()
			groups = []
			membership = False
			for group in dcobject.get('groups'):
				groups.append(group.lower())
			for dcgroup in dcgroups:
				if dcgroup.lower() in groups:
					membership = True

			if is_master_or_backup and membership:
				raise DCMembership()
			elif not is_master_or_backup and not membership:
				raise DCMembership()

		ucr.load()
		if not singlemaster:
			# in multiserver setups all dhcp settings have to be checked
			dhcp_dn = "cn=dhcp,%s" % (ou_base)
		else:
			# in singleserver setup only the first OU sets dhcpd/ldap/base and all following OUs
			# should leave the UCR variable untouched.
			dhcpd_ldap_base = ucr.get('dhcpd/ldap/base')
			if not dhcpd_ldap_base or 'ou=' not in dhcpd_ldap_base:
				raise DhcpdLDAPBase('dhcpd/ldap/base=%r contains no "ou="' % (dhcpd_ldap_base,))

			if not old_dhcpd_ldap_base:
				# seems to be the first OU, so check the variable settings
				if ucr.get('dhcpd/ldap/base') != "cn=dhcp,%s" % (ou_base,):
					print 'ERROR: dhcpd/ldap/base =', ucr.get('dhcpd/ldap/base')
					print 'ERROR: expected base =', dhcp_dn
					raise DhcpdLDAPBase()

			# use the UCR value and check if the DHCP service exists
			dhcp_dn = dhcpd_ldap_base

		# dhcp
		print 'LDAP base of dhcpd = %r' % dhcp_dn
		dhcp_service_dn = "cn=%s,%s" % (get_school_ou_from_dn(dhcp_dn, ucr), dhcp_dn)
		dhcp_server_dn = "cn=%s,%s" % (dc_name, dhcp_service_dn)
		if must_exist:
			utils.verify_ldap_object(dhcp_service_dn, expected_attr={'dhcpOption': ['wpad "http://%s.%s/proxy.pac"' % (dc_name, ucr.get('domainname'))]}, should_exist=True)
			utils.verify_ldap_object(dhcp_server_dn, should_exist=True)

		dhcp_dns_clearou_dn = 'cn=dhcp-dns-clear,cn=policies,%s' % ou_base
		if dhcp_dns_clearou:
			utils.verify_ldap_object(dhcp_dns_clearou_dn, expected_attr={'emptyAttributes': ['univentionDhcpDomainNameServers']}, should_exist=must_exist)
			try:
				utils.verify_ldap_object(ou_base, expected_attr={'univentionPolicyReference': [dhcp_dns_clearou_dn]}, should_exist=must_exist)
			except utils.LDAPObjectUnexpectedValue:
				# ignore other policies
				pass
		else:
			utils.verify_ldap_object(dhcp_dns_clearou_dn, should_exist=False)
