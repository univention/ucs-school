#!/usr/share/ucs-test/runner python
# coding=utf-8
## desc: dump LDAP access to all available objects
## roles: [domaincontroller_master]
## tags: [ucsschool,ucsschool_base1]
## timeout: 3600
## exposure: dangerous
## packages: [ucs-school-ldap-acls-master]

import re
import os
import time
import subprocess
from multiprocessing import Pool
import ldif

from univention.testing.ucsschool.ucs_test_school import AutoMultiSchoolEnv, logger

try:
	from typing import Dict, List, Optional, Set
except ImportError:
	pass

# OUTPUT of "slapacl -d0 -D cn=admin,dc=nstx,dc=local -b uid=Administrator,cn=users,dc=nstx,dc=local 2>&1"
# ==> PLEASE NOTE THAT BINARY VALUES (LIKE "KRB5KEY") MAY CONTAIN LINEBREAKS THAT MAKE PARSING HARDER!
#
# authcDN: "cn=admin,dc=nstx,dc=local"
# entry: manage(=mwrscxd)
# children: manage(=mwrscxd)
# uid=Administrator: manage(=mwrscxd)
# krb5PrincipalName=Administrator@NSTX.LOCAL: manage(=mwrscxd)
# uidNumber=2002: manage(=mwrscxd)
# sambaAcctFlags=[U          ]: manage(=mwrscxd)
# krb5MaxLife=86400: manage(=mwrscxd)
# cn=Administrator: manage(=mwrscxd)
# krb5MaxRenew=604800: manage(=mwrscxd)
# loginShell=/bin/bash: manage(=mwrscxd)
# univentionObjectType=users/user: manage(=mwrscxd)
# displayName=Administrator: manage(=mwrscxd)
# sambaSID=S-1-5-21-3846281231-3184689532-2158317326-500: manage(=mwrscxd)
# gecos=Administrator: manage(=mwrscxd)
# sn=Administrator: manage(=mwrscxd)
# homeDirectory=/home/Administrator: manage(=mwrscxd)
# structuralObjectClass=inetOrgPerson: manage(=mwrscxd)
# entryUUID=c711836e-92a3-1036-98ae-19810040644d: manage(=mwrscxd)
# creatorsName=cn=admin,dc=nstx,dc=local: manage(=mwrscxd)
# createTimestamp=20170301082113Z: manage(=mwrscxd)
# univentionPolicyReference=cn=default-admins,cn=admin-settings,cn=users,cn=policies,dc=nstx,dc=local: manage(=mwrscxd)
# objectClass=krb5KDCEntry: manage(=mwrscxd)
# objectClass=univentionPerson: manage(=mwrscxd)
# objectClass=person: manage(=mwrscxd)
# objectClass=automount: manage(=mwrscxd)
# objectClass=top: manage(=mwrscxd)
# objectClass=inetOrgPerson: manage(=mwrscxd)
# objectClass=sambaSamAccount: manage(=mwrscxd)
# objectClass=organizationalPerson: manage(=mwrscxd)
# objectClass=univentionPWHistory: manage(=mwrscxd)
# objectClass=univentionMail: manage(=mwrscxd)
# objectClass=univentionObject: manage(=mwrscxd)
# objectClass=shadowAccount: manage(=mwrscxd)
# objectClass=krb5Principal: manage(=mwrscxd)
# objectClass=univentionPolicyReference: manage(=mwrscxd)
# objectClass=posixAccount: manage(=mwrscxd)
# univentionUMCProperty=appcenterSeen=2: manage(=mwrscxd)
# univentionUMCProperty=favorites=appcenter:appcenter,updater,udm:users/user,udm:groups/group,udm:computers/computer,apps:ucsschool: manage(=mwrscxd)
# description=Built-in account for administering the computer/domain: manage(=mwrscxd)
# shadowLastChange=17229: manage(=mwrscxd)
# gidNumber=5001: manage(=mwrscxd)
# sambaPrimaryGroupSID=S-1-5-21-3846281231-3184689532-2158317326-513: manage(=mwrscxd)
# pwhistory=$6$vRMTALPNn0OeUf/5$9Ql3H5jhwHMIfM8q816e/usMSViXY3S0R5l1YejNk6718aGPInlzKu0ZpSbiHGwtAN2Lz2IoHVxCBBfX7Td8B0 $6$oVtqfZgD.GRL1Lm2$F5b.NQQQjmNji56fOdAQoa04yH5SjBE6zjqGgIKiF43ubKSLDWAqQlorTMJYnGqH9ROTQ0zeki9t52jmjQPuK1 $6$mg9.eCcNgoszfFT3$PffIE27/wXxgmIgg2droezrLizh0xIMCmcHbSnNi.H/F8PAYB.0aQVI4hwTqe95uBTalyBXgsOIKcQ6pXczox1: manage(=mwrscxd)
# userPassword=****: manage(=mwrscxd)
# sambaNTPassword=CAA1239D44DA7EDF926BCE39F5C65D0F: manage(=mwrscxd)
# sambaPasswordHistory=390CFF5B17A555A5DB5BF14533A4B6E91AB9F6F3B25B4301BAF338FFAFC3442CDF15C89035597E162593E89108CD5775F1B3FE39C0B1711E05FBC38753CE22FE1863FE4A700E8A97B4BA601D207E57B0C67F70737659810F6BA6C3E231E8D0067B8149DCF354038D43EB671B6A55AB03D9A9E98FCFD02A424608FB0747DE1FF6: manage(=mwrscxd)
# krb5Key=0Q<A1>+0)<A0>^C^B^A^R<A1>"^D ((<9F>VQ;}yo<AF>^F<A2><D6>^Z^O^g<A4><E4>x<BD>=^B<98><EF><CC>`<DB>R<97><ED>!<A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5Key=0A<A1>ESC0^Y<A0>^C^B^A^Q<A1>^R^D^P<DE><C9>^ZGp̏{<AA>^F<96><9E>N/<A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5Key=0I<A1>#0!<A0>^C^B^A^P<A1>^Z^D^X<C1><E9>><E9>v<8A>^B#^?<D0>h^P)4F#^D굑)^S^K<EC><A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5Key=0A<A1>ESC0^Y<A0>^C^B^A^W<A1>^R^D^Pʡ#<9D>D<DA>~ߒk<CE>9<F5><C6>]^O<A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5Key=09<A1>^S0^Q<A0>^C^B^A^C<A1>
# ^D^HpWu;zb<A4>^Y<A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5Key=09<A1>^S0^Q<A0>^C^B^A^B<A1>
# ^D^HpWu;zb<A4>^Y<A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5Key=09<A1>^S0^Q<A0>^C^B^A^A<A1>
# ^D^HpWu;zb<A4>^Y<A2>"0 <A0>^C^B^A^C<A1>^Y^D^WNSTX.LOCALAdministrator: manage(=mwrscxd)
# krb5KDCFlags=126: manage(=mwrscxd)
# krb5KeyVersionNumber=4: manage(=mwrscxd)
# sambaPwdLastSet=1489162588: manage(=mwrscxd)
# entryCSN=20170310161628.837230Z#000000#000#000000: manage(=mwrscxd)
# modifiersName=uid=Administrator,cn=users,dc=nstx,dc=local: manage(=mwrscxd)
# modifyTimestamp=20170310161628Z: manage(=mwrscxd)


def normalize_permission(perms):
	level_to_priv = {
		'none': '0',
		'disclose': 'd',
		'auth': 'xd',
		'compare': 'cxd',
		'search': 'scxd',
		'read': 'rscxd',
		'write': 'wrscxd',
		'add': 'arscxd',
		'delete': 'zrscxd',
		'manage': 'mwrscxd',
	}
	if not perms.startswith('='):
		perms = '=%s' % level_to_priv[perms.split('(', 1)[0]]
	return perms


def run_one_test(args):
	result_dir, thread_id, binddn, dn_list = args
	try:
		output = open(os.path.join(result_dir, 'dn%02d.ldif' % (thread_id,)), 'wb')
		time_start = time.time()
		writer = ldif.LDIFWriter(output)

		len_dn_list = len(dn_list)
		for j, dn in enumerate(dn_list):
			if j % 50 == 0:
				logger.debug('Process %02d (pid %d): %05d/%05d', thread_id, os.getpid(), j, len_dn_list)
				for handler in logger.handlers:
					handler.flush()
			entry = {}  # type: Dict[str, Set[str]]
			cmd = ['slapacl', '-d0', '-D', binddn, '-b', dn]
			process = subprocess.Popen(cmd, stderr=subprocess.PIPE)
			_, stderr = process.communicate()
			for line in re.findall('^(?:[a-zA-Z0-9]+=.*?: .*?=[a-z0]+[)]?|entry: .*?|children: .*?)$', stderr, re.DOTALL | re.MULTILINE):
				attr, value = line.rsplit(': ', 1)
				attr = attr.split('=', 1)[0]
				if attr not in ('authcDN',):  # ignore some attributes
					entry.setdefault(attr, set()).add(normalize_permission(value.strip()))
			writer.unparse(dn, entry)
		msg = '*** Runtime for parse_acls(Process %02d - pid %d): %fs' % (thread_id, os.getpid(), time.time() - time_start,)
	except Exception:
		logger.exception('TRACEBACK IN PROCESS %d (%s):', thread_id, binddn)
		raise
	return msg


class LDAPDiffCheck(AutoMultiSchoolEnv):
	def __init__(self):  # type: () -> None
		super(LDAPDiffCheck, self).__init__()
		self.dn_list = None  # type: Optional[List[str]]

	def collect_dns(self, valid_ou_names=None):
		valid_ous = valid_ou_names or [',ou=%s' % (x,) for x in [self.schoolA.name, self.schoolB.name, self.schoolC.name, 'Domain Controllers']]
		self.dn_list = [dn for dn in self.lo.searchDn() if (
			(not dn.startswith('ou=') and (',ou=' not in dn)) or    # accept all NON-OU objects
			(any([x in dn for x in valid_ous])))]                   # and all objects of "valid" OUs to get comparable results

	def run_all_tests(self, result_dir):
		os.makedirs(result_dir)

		pool = Pool()  # uses NUMBER_OF_CPUS worker processes by default

		work_items = [(result_dir, i, binddn, self.dn_list) for i, binddn in enumerate([
			'cn=admin,%(ldap/base)s' % self.ucr,
			self.generic.master.dn,
			self.generic.backup.dn,
			self.generic.slave.dn,
			self.generic.member.dn,
			self.generic.winclient.dn,
			'uid=Administrator,cn=users,%(ldap/base)s' % self.ucr,
			self.generic.domain_user.dn,
			self.schoolA.schoolserver.dn,
			self.schoolB.schoolserver.dn,
			self.schoolC.schoolserver.dn,
			self.schoolA.winclient.dn,
			self.schoolB.winclient.dn,
			self.schoolC.winclient.dn,
			self.schoolA.teacher.dn,
			self.schoolB.teacher.dn,
			self.schoolC.teacher.dn,
			self.schoolA.student.dn,
			self.schoolB.student.dn,
			self.schoolC.student.dn,
			self.schoolA.teacher_staff.dn,
			self.schoolB.teacher_staff.dn,
			self.schoolC.teacher_staff.dn,
			self.schoolA.staff.dn,
			self.schoolB.staff.dn,
			self.schoolC.staff.dn,
			self.schoolA.admin1.dn,
			self.schoolB.admin1.dn,
			self.schoolC.admin1.dn,
		])]
		for result_dir, i, binddn, _ in work_items:
			with open(os.path.join(result_dir, 'dn.txt'), 'a+') as fd:
				fd.write('%02d ==> %s\n' % (i, binddn))

		results = pool.imap_unordered(run_one_test, work_items)
		logger.info('DONE')
		logger.info(repr(results))
		for result in results:
			logger.info(result)


def main():
	with LDAPDiffCheck() as test_suite:
		test_suite.collect_dns()

		testdir = '/var/log/univention/78_ldap_acls_dump.{}'.format(int(time.time()))
		test_suite.create_multi_env_global_objects()
		test_suite.create_multi_env_school_objects()
		test_suite.run_all_tests(testdir)

		logger.info('Use following command for diff:')
		logger.info('./78_ldap_acls_dump.diff')

		# for debugging purposes
		if os.path.exists('/tmp/78_ldap_acls_dump.debug'):
			fn = '/tmp/78_ldap_acls_dump.continue'
			logger.info('=== DEBUGGING MODE ===')
			logger.info('Waiting for cleanup until %r exists...', fn)
			while not os.path.exists(fn):
				time.sleep(1)


if __name__ == '__main__':
	main()
