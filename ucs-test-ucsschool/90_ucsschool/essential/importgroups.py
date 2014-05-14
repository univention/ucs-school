## -*- coding: utf-8 -*-

import os
import string
import subprocess
import tempfile
import univention.testing.utils as utils
import univention.testing.strings as uts
from ucsschool.lib.models import SchoolClass as GroupLib
from ucsschool.lib.models import School as SchoolLib
import ucsschool.lib.models.utils

from essential.importou import remove_ou, get_school_base

HOOK_BASEDIR = '/usr/share/ucs-school-import/hooks'

class ImportGroup(Exception):
	pass
class GroupHookResult(Exception):
	pass

import univention.config_registry
configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()

cn_pupils = configRegistry.get('ucsschool/ldap/default/container/pupils', 'schueler')

class Group:
	def __init__(self, school):
		self.name = uts.random_name()
		self.description = uts.random_name()
		self.school = school
		self.mode = 'A'

		self.school_base = get_school_base(self.school)

		self.dn = 'cn=%s,cn=klassen,cn=%s,cn=groups,%s' % (self.name, cn_pupils, self.school_base)
		self.share_dn = 'cn=%s,cn=klassen,cn=shares,%s' % (self.name, self.school_base)

	def set_mode_to_modify(self):
		self.mode = 'M'
	def set_mode_to_delete(self):
		self.mode = 'D'

	def __str__(self):
		delimiter = '\t'
		line = self.mode
		line += delimiter
		line += self.school
		line += delimiter
		line += self.name
		line += delimiter
		line += self.description
		return line

	def expected_attributes(self):
		attr = {}
		attr['cn'] = [self.name]
		attr['description'] = [self.description]
		return attr

	def verify(self):
		print 'verify group: %s' % self.name

		if self.mode == 'D':
			utils.verify_ldap_object(self.dn, should_exist=False)
			utils.verify_ldap_object(self.share_dn, should_exist=False)
			return

		utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)
		utils.verify_ldap_object(self.share_dn, should_exist=True)


class ImportFile:
	def __init__(self, use_cli_api, use_python_api):
		self.use_cli_api = use_cli_api
		self.use_python_api = use_python_api
		self.import_fd, self.import_file = tempfile.mkstemp()
		os.close(self.import_fd)
		self.group_import = None

	def write_import(self):
		self.import_fd = os.open(self.import_file, os.O_RDWR|os.O_CREAT)
		os.write(self.import_fd, str(self.group_import))
		os.close(self.import_fd)

	def run_import(self, group_import):
		hooks = GroupHooks()
		self.group_import = group_import
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
			print 'SCHOOL DATA     :\n%s' % str(self.group_import)
			if pre_result != post_result != str(self.group_import):
				raise GroupHookResult()
		finally:
			hooks.cleanup()
			try:
				os.remove(self.import_file)
			except OSError as e:
				print 'WARNING: %s not removed. %s' % (self.import_file, e)

	def _run_import_via_cli(self):
		cmd_block = ['/usr/share/ucs-school-import/scripts/import_group', self.import_file]

		print 'cmd_block: %r' % cmd_block
		retcode = subprocess.call(cmd_block, shell=False)
		if retcode:
			raise ImportGroup('Failed to execute "%s". Return code: %d.' % (string.join(cmd_block), retcode))

	def _run_import_via_python_api(self):
		
		# reload UCR
		ucsschool.lib.models.utils.ucr.load()

		lo = univention.admin.uldap.getAdminConnection()[0]

		# get school from first group
		school = self.group_import.groups[0].school

		school_obj = SchoolLib.cache(school, display_name=school)
		if not school_obj.exists(lo):
			school_obj.dc_name = uts.random_name()
			school_obj.create(lo)

		for grp in self.group_import.groups:
			kwargs = {'school': grp.school, 'name': grp.name, 'description': grp.description}
			if grp.mode == 'A':
				GroupLib(**kwargs).create(lo)
			elif grp.mode == 'M':
				GroupLib(**kwargs).modify(lo)
			elif grp.mode == 'D':
				GroupLib(**kwargs).remove(lo)

class GroupHooks:
	def __init__(self):
		fd, self.pre_hook_result = tempfile.mkstemp()
		os.close(fd)

		fd, self.post_hook_result = tempfile.mkstemp()
		os.close(fd)

		self.create_hooks()

	def get_pre_result(self):
		return open(self.pre_hook_result, 'r').read()
	def get_post_result(self):
		return open(self.post_hook_result, 'r').read()

	def create_hooks(self):
		self.pre_hooks = [
				os.path.join(os.path.join(HOOK_BASEDIR, 'group_create_pre.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'group_remove_pre.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'group_modify_pre.d'), uts.random_name()),
		]

		self.post_hooks = [
				os.path.join(os.path.join(HOOK_BASEDIR, 'group_create_post.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'group_modify_post.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'group_remove_post.d'), uts.random_name()),
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
name="$(cat $1 | awk -F '\t' '{print $3}')"
mode="$(cat $1 | awk -F '\t' '{print $1}')"
if [ "$mode" != D ]; then
	ldap_dn="$(univention-ldapsearch "(&(objectClass=univentionGroup)(cn=$name))" | ldapsearch-wrapper | sed -ne 's|dn: ||p')"
	test "$dn" = "$ldap_dn" || exit 1
fi
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

class GroupImport:
	def __init__(self, nr_groups=20):
		assert (nr_groups > 3)

		self.school = uts.random_name()

		self.groups = []
		for i in range(0, nr_groups):
			self.groups.append(Group(self.school))

	def __str__(self):
		lines = []

		for group in self.groups:
			lines.append(str(group))

		return '\n'.join(lines)

	def verify(self):
		for group in self.groups:
			group.verify()

	def modify(self):
		for group in self.groups:
			group.set_mode_to_modify()
		self.groups[0].description = uts.random_name()
		self.groups[1].description = uts.random_name()

	def delete(self):
		for group in self.groups:
			group.set_mode_to_delete()

def create_and_verify_groups(use_cli_api=True, use_python_api=False, nr_groups=5):
	assert(use_cli_api != use_python_api)

	print '********** Generate school data'
	group_import = GroupImport(nr_groups=nr_groups)
	import_file = ImportFile(use_cli_api, use_python_api)

	print group_import

	try:
		print '********** Create groups'
		import_file.run_import(group_import)
		group_import.verify()

		print '********** Modify groups'
		group_import.modify()
		import_file.run_import(group_import)
		group_import.verify()

		print '********** Delete groups'
		group_import.delete()
		import_file.run_import(group_import)
		group_import.verify()

	finally:
		remove_ou(group_import.school)


def import_groups_basics(use_cli_api=True, use_python_api=False):
	create_and_verify_groups(use_cli_api, use_python_api, 10)

