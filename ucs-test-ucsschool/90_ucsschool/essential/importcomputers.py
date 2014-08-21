## -*- coding: utf-8 -*-

import os
import random
import string
import subprocess
import tempfile
import univention.testing.utils as utils
import univention.testing.strings as uts
#from ucsschool.lib.models import SchoolComputer as SchoolComputerLib
from ucsschool.lib.models import WindowsComputer as WindowsComputerLib
from ucsschool.lib.models import MacComputer as MacComputerLib
from ucsschool.lib.models import IPComputer as IPComputerLib
#from ucsschool.lib.models import UCCComputer as UCCComputerLib
from ucsschool.lib.models import School as SchoolLib
import ucsschool.lib.models.utils

from essential.importou import remove_ou, get_school_base

HOOK_BASEDIR = '/usr/share/ucs-school-import/hooks'

class ImportComputer(Exception):
	pass
class ComputerHookResult(Exception):
	pass
class WrongMembership(Exception):
	pass

import univention.config_registry
configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()


def random_mac():
	mac = [
		random.randint(0x00, 0x7f),
		random.randint(0x00, 0x7f),
		random.randint(0x00, 0x7f),
		random.randint(0x00, 0x7f),
		random.randint(0x00, 0xff),
		random.randint(0x00, 0xff)
	]

	return ':'.join(map(lambda x: "%02x" % x, mac))

def random_ip():
	return ".".join(map(str, (random.randint(1, 254) for _ in range(4))))

class Computer:
	def __init__(self, school, ctype):
		self.name = uts.random_name()
		self.mac = random_mac()
		self.ip = random_ip()
		self.school = school
		self.ctype = ctype

		self.inventorynumbers = []
		self.zone = None

		self.school_base = get_school_base(self.school)

		self.dn = 'cn=%s,cn=computers,%s' % (self.name, self.school_base)


	def set_inventorynumbers(self):
		self.inventorynumbers.append(uts.random_name())
		self.inventorynumbers.append(uts.random_name())
	def set_zone_verwaltung(self):
		if self.ctype == 'memberserver':
			self.zone = 'verwaltung'
	def set_zone_edukativ(self):
		if self.ctype == 'memberserver':
			self.zone = 'edukativ'

	def __str__(self):
		delimiter = '\t'
		line = self.ctype
		line += delimiter
		line += self.name
		line += delimiter
		line += self.mac
		line += delimiter
		line += self.school
		line += delimiter
		line += self.ip
		line += delimiter
		if self.inventorynumbers:
			line += ','.join(self.inventorynumbers)
		if self.zone:
			line += delimiter
			line += self.zone

		return line

	def expected_attributes(self):
		attr = {}
		attr['cn'] = [self.name]
		attr['macAddress'] = [self.mac]
		attr['aRecord'] = [self.ip]
		if self.inventorynumbers:
			attr['univentionInventoryNumber'] = self.inventorynumbers
		attr['univentionObjectType'] = ['computers/%s' % self.ctype]

		return attr

	def verify(self):
		print 'verify computer: %s' % self.name

		utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)

		verwaltung_member_group1 = 'cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (self.school, configRegistry.get('ldap/base'))
		verwaltung_member_group2 = 'cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (configRegistry.get('ldap/base'))
		edukativ_member_group1 = 'cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s' % (self.school, configRegistry.get('ldap/base'))
		edukativ_member_group2 = 'cn=Member-Edukativnetz,cn=ucsschool,cn=groups,%s' % (configRegistry.get('ldap/base'))
		if self.zone == 'verwaltung':
			utils.verify_ldap_object(verwaltung_member_group1, expected_attr={'uniqueMember': [self.dn]}, strict=False, should_exist=True)
			utils.verify_ldap_object(verwaltung_member_group2, expected_attr={'uniqueMember': [self.dn]}, strict=False, should_exist=True)
		else:
			for group_dn in [verwaltung_member_group1, verwaltung_member_group2]:
				try:
					utils.verify_ldap_object(group_dn, expected_attr={'uniqueMember': [self.dn]}, strict=False, should_exist=True)
					raise WrongMembership()
				except utils.LDAPObjectValueMissing:
					pass
		if self.zone == 'edukativ':
			utils.verify_ldap_object(edukativ_member_group1, expected_attr={'uniqueMember': [self.dn]}, strict=False, should_exist=True)
			utils.verify_ldap_object(edukativ_member_group2, expected_attr={'uniqueMember': [self.dn]}, strict=False, should_exist=True)
		else:
			for group_dn in [edukativ_member_group1, edukativ_member_group2]:
				try:
					utils.verify_ldap_object(group_dn, expected_attr={'uniqueMember': [self.dn]}, strict=False, should_exist=True)
					raise WrongMembership()
				except utils.LDAPObjectValueMissing:
					pass


class Windows(Computer):
	def __init__(self, school):
		Computer.__init__(self, school, 'windows')

class Memberserver(Computer):
	def __init__(self, school):
		Computer.__init__(self, school, 'memberserver')

class MacOS(Computer):
	def __init__(self, school):
		Computer.__init__(self, school, 'macos')

class IPManagedClient(Computer):
	def __init__(self, school):
		Computer.__init__(self, school, 'ipmanagedclient')

class ImportFile:
	def __init__(self, use_cli_api, use_python_api):
		self.use_cli_api = use_cli_api
		self.use_python_api = use_python_api
		self.import_fd, self.import_file = tempfile.mkstemp()
		os.close(self.import_fd)
		self.computer_import = None

	def write_import(self):
		self.import_fd = os.open(self.import_file, os.O_RDWR|os.O_CREAT)
		os.write(self.import_fd, str(self.computer_import))
		os.close(self.import_fd)

	def run_import(self, computer_import):
		hooks = ComputerHooks()
		self.computer_import = computer_import
		try:
			if self.use_cli_api:
				self.write_import()
				self._run_import_via_cli()
			elif self.use_python_api:
				self._run_import_via_python_api()
			pre_result = hooks.get_pre_result()
			post_result = hooks.get_post_result()
			print 'PRE  HOOK result:\n%s' % pre_result
			print 'POST HOOK result:\n%s' % post_result
			print 'SCHOOL DATA     :\n%s' % str(self.computer_import)
			if pre_result != post_result != str(self.computer_import):
				raise ComputerHookResult()
		finally:
			hooks.cleanup()
			try:
				os.remove(self.import_file)
			except OSError as e:
				print 'WARNING: %s not removed. %s' % (self.import_file, e)

	def _run_import_via_cli(self):
		cmd_block = ['/usr/share/ucs-school-import/scripts/import_computer', self.import_file]

		print 'cmd_block: %r' % cmd_block
		retcode = subprocess.call(cmd_block, shell=False)
		if retcode:
			raise ImportComputer('Failed to execute "%s". Return code: %d.' % (string.join(cmd_block), retcode))

	def _run_import_via_python_api(self):
		# reload UCR
		ucsschool.lib.models.utils.ucr.load()

		lo = univention.admin.uldap.getAdminConnection()[0]

		# get school from first computer
		school = self.computer_import.windows[0].school

		school_obj = SchoolLib.cache(school, display_name=school)
		if not school_obj.exists(lo):
			school_obj.dc_name = uts.random_name()
			school_obj.create(lo)

		def _set_kwargs(computer):
			kwargs = {
					'school': computer.school,
					'name': computer.name,
					'ip_address': computer.ip,
					'mac_address': computer.mac,
					'type_name': computer.ctype,
					'inventory_number': computer.inventorynumbers,
					'zone': computer.zone,
			}
			return kwargs

		for computer in self.computer_import.windows:
			kwargs = _set_kwargs(computer)
			WindowsComputerLib(**kwargs).create(lo)
		# for computer in self.computer_import.memberservers:
		# 	kwargs = _set_kwargs(computer)
		# 	IPComputerLib(**kwargs).create(lo)
		for computer in self.computer_import.macos:
			kwargs = _set_kwargs(computer)
			MacComputerLib(**kwargs).create(lo)
		for computer in self.computer_import.ipmanagedclients:
			kwargs = _set_kwargs(computer)
			IPComputerLib(**kwargs).create(lo)

class ComputerHooks:
	def __init__(self):
		fd, self.pre_hook_result = tempfile.mkstemp()
		os.close(fd)

		fd, self.post_hook_result = tempfile.mkstemp()
		os.close(fd)

		self.pre_hooks = []
		self.post_hooks = []

		self.create_hooks()

	def get_pre_result(self):
		return open(self.pre_hook_result, 'r').read()
	def get_post_result(self):
		return open(self.post_hook_result, 'r').read()

	def create_hooks(self):
		self.pre_hooks = [
				os.path.join(os.path.join(HOOK_BASEDIR, 'computer_create_pre.d'), uts.random_name()),
		]

		self.post_hooks = [
				os.path.join(os.path.join(HOOK_BASEDIR, 'computer_create_post.d'), uts.random_name()),
		]

		for pre_hook in self.pre_hooks:
			with open(pre_hook, 'w+') as fd:
				fd.write('''#!/bin/sh
set -x
test $# = 1 || exit 1
cat $1 >>%(pre_hook_result)s
exit 0
''' % {'pre_hook_result': self.pre_hook_result})
			os.chmod(pre_hook, 0755)

		for post_hook in self.post_hooks:
			with open(post_hook, 'w+') as fd:
				fd.write('''#!/bin/sh
set -x
dn="$2"
name="$(cat $1 | awk -F '\t' '{print $2}')"
type="$(cat $1 | awk -F '\t' '{print $1}')"
ldap_dn="$(univention-ldapsearch "(&(cn=$name)(univentionObjectType=computers/$type))" | ldapsearch-wrapper | sed -ne 's|dn: ||p')"
test "$dn" = "$ldap_dn" || exit 1
cat $1 >>%(post_hook_result)s
exit 0
''' % {'post_hook_result': self.post_hook_result})
			os.chmod(post_hook, 0755)

	def cleanup(self):
		for pre_hook in self.pre_hooks:
			os.remove(pre_hook)
		for post_hook in self.post_hooks:
			os.remove(post_hook)
		os.remove(self.pre_hook_result)
		os.remove(self.post_hook_result)

class ComputerImport:
	def __init__(self, nr_windows=20, nr_memberserver=10, nr_macos=5, nr_ipmanagedclient=3):
		assert (nr_windows > 2)
		assert (nr_macos > 2)
		assert (nr_ipmanagedclient > 2)

		self.school = uts.random_name()

		self.windows = []
		for i in range(0, nr_windows):
			self.windows.append(Windows(self.school))
		self.windows[1].set_inventorynumbers()
		self.windows[2].set_zone_verwaltung()

		self.memberservers = []
		for i in range(0, nr_memberserver):
			self.memberservers.append(Memberserver(self.school))
		if self.memberservers:
			self.memberservers[2].set_inventorynumbers()
			self.memberservers[0].set_zone_verwaltung()

		self.macos = []
		for i in range(0, nr_macos):
			self.macos.append(MacOS(self.school))
		self.macos[0].set_inventorynumbers()
		self.macos[1].set_zone_edukativ()

		self.ipmanagedclients = []
		for i in range(0, nr_ipmanagedclient):
			self.ipmanagedclients.append(IPManagedClient(self.school))
		self.ipmanagedclients[0].set_inventorynumbers()
		self.ipmanagedclients[0].set_zone_edukativ()
		self.ipmanagedclients[1].set_zone_edukativ()

	def __str__(self):
		lines = []

		for windows in self.windows:
			lines.append(str(windows))

		for memberserver in self.memberservers:
			lines.append(str(memberserver))

		for macos in self.macos:
			lines.append(str(macos))

		for ipmanagedclient in self.ipmanagedclients:
			lines.append(str(ipmanagedclient))

		return '\n'.join(lines)

	def verify(self):
		for windows in self.windows:
			windows.verify()

		for memberserver in self.memberservers:
			memberserver.verify()

		for macos in self.macos:
			macos.verify()

		for ipmanagedclient in self.ipmanagedclients:
			ipmanagedclient.verify()


def create_and_verify_computers(use_cli_api=True, use_python_api=False, nr_windows=20, nr_memberserver=10, nr_macos=5, nr_ipmanagedclient=3):
	assert(use_cli_api != use_python_api)

	print '********** Generate school data'
	computer_import = ComputerImport(nr_windows=nr_windows, nr_memberserver=nr_memberserver, nr_macos=nr_macos, nr_ipmanagedclient=nr_ipmanagedclient)
	import_file = ImportFile(use_cli_api, use_python_api)

	print computer_import

	try:
		print '********** Create computers'
		import_file.run_import(computer_import)
		computer_import.verify()

	finally:
		remove_ou(computer_import.school)


def import_computers_basics(use_cli_api=True, use_python_api=False, nr_memberserver=4):
	create_and_verify_computers(use_cli_api, use_python_api, 5, nr_memberserver, 3, 3)

