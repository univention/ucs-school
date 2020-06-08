#!/usr/share/ucs-test/runner python
# coding=utf-8
## desc: check if staff users can optionally be replicated to edu slaves
## roles: [domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## timeout: 3600
## exposure: dangerous
## packages: [ucs-school-slave]
## bugs: [50274]


from __future__ import absolute_import
from __future__ import print_function
import subprocess
import univention.admin.uldap as udm_uldap
import univention.testing.utils as utils
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool, NameDnObj, logger


class LDAPACLCheck(UCSTestSchool):
	def __init__(self, *args, **kwargs):
		super(LDAPACLCheck, self).__init__(*args, **kwargs)
		account = utils.UCSTestDomainAdminCredentials()
		self.admin_username = account.username
		self.admin_password = account.bindpw
		self.master_fqdn = self.ucr.get('ldap/master')

	def setup(self):  # type: () -> None
		self.school = NameDnObj()
		self.school.name, self.school.dn = self.create_ou(name_edudc=self.ucr.get('hostname'))
		self.teacher_user = NameDnObj(*self.create_user(self.school.name, is_teacher=True))
		logger.debug('TEACHER DN: %s', self.teacher_user.dn)
		logger.debug('TEACHER NAME: %s', self.teacher_user.name)
		self.staff_user = NameDnObj()

	def run_on_master(self, command_line):  # type: (str) -> Tuple[str, str]
		cmd = ('univention-ssh', '-timeout', '120', '/dev/stdin', 'root@{}'.format(self.master_fqdn), command_line)
		logger.info('CMD: %s', ' '.join(cmd))
		proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = proc.communicate(self.admin_password)
		return stdout, stderr

	def run_test(self):  # type: () -> None
		# ssh to master ==> get UCR + set to OFF
		stdout, stderr = self.run_on_master('/usr/sbin/ucr get ucsschool/ldap/replicate_staff_to_edu')
		logger.debug('STDOUT:\n%s', stdout)
		logger.debug('STDERR:\n%s', stderr)
		old_value = stdout.strip()
		logger.info('OLD VALUE: %r', old_value)

		try:
			# HINT:
			# the case ucsschool/ldap/replicate_staff_to_edu=no is not tested, because this is currently the default case
			# and it is difficult to test e.g. via verify_ldap_object() since it does not use the machine account

			# ssh to master ==> set UCRV to ON and create Staff2 in test OU
			stdout, stderr = self.run_on_master(
				'/usr/sbin/ucr set ucsschool/ldap/replicate_staff_to_edu=yes ; '
				'/usr/sbin/ucr commit /etc/ldap/slapd.conf ; '
				'/usr/sbin/service slapd restart')
			logger.debug('STDOUT:\n%s', stdout)
			logger.debug('STDERR:\n%s', stderr)

			# create Staff in test OU
			# check if staff is locally available
			self.staff_user = NameDnObj(*self.create_user(self.school.name, is_staff=True))

			# test with Administrator account
			utils.verify_ldap_object(self.staff_user.dn, {
				'uid': [self.staff_user.name],
			}, should_exist=True, retry_count=10, delay=3)

			# test with teacher account
			lo = udm_uldap.access(
				host=self.ucr.get('ldap/server/name'),
				port=7389,
				base=self.ucr.get('ldap/base'),
				binddn=self.teacher_user.dn,
				bindpw='univention',
				start_tls=2)
			assert lo.search(base=self.staff_user.dn, scope='base'), "teacher is unable to find staff user"

			# test with machine account
			lo = self.open_ldap_connection(machine=True, ldap_server=self.ucr.get('ldap/server/name'))
			assert lo.search(base=self.staff_user.dn, scope='base'), "machine account is unable to find staff user"
		finally:
			cmd_list = [
				'/usr/sbin/ucr set ucsschool/ldap/replicate_staff_to_edu={}'.format(old_value),
				'/usr/sbin/ucr commit /etc/ldap/slapd.conf',
				'/usr/sbin/service slapd restart',
			]
			if not old_value:
				cmd_list[0] = '/usr/sbin/ucr unset ucsschool/ldap/replicate_staff_to_edu'
			stdout, stderr = self.run_on_master(' ; '.join(cmd_list))
			logger.debug('STDOUT:\n%s', stdout)
			logger.debug('STDERR:\n%s', stderr)


def main():
	with LDAPACLCheck() as test_suite:
		test_suite.setup()
		test_suite.run_test()


if __name__ == '__main__':
	main()
