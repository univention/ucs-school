#!/usr/share/ucs-test/runner python
# -*- coding: utf-8 -*-
## desc: Test execution of legacy hooks
## exposure: dangerous
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## packages: [python-ucs-school, ucs-school-import]
## bugs: [49556]

import os
import re
import os.path
import inspect
import pprint
import importlib
from unittest import main, TestCase
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models import Group, School
from ucsschool.importer.configuration import setup_configuration
from ucsschool.importer.factory import setup_factory
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine
import univention.testing.strings as uts
from univention.testing.ucsschool.importcomputers import random_ip
from univention.testing.ucsschool.importcomputers import random_mac
from univention.testing.ucsschool.ucs_test_school import get_ucsschool_logger, UCSTestSchool
try:
	from typing import Type
except ImportError:
	pass

MODULE_PATHS = (
	('/usr/share/pyshared/ucsschool/lib/models', 'ucsschool.lib.models'),
	('/usr/share/pyshared/ucsschool/importer/models', 'ucsschool.importer.models'),
	('/usr/share/pyshared/ucsschool/importer/legacy', 'ucsschool.importer.legacy'),
)
BASE_CLASS = UCSSchoolHelperAbstractClass
TEST_HOOK_SOURCE = os.path.join(os.path.dirname(__file__), 'test82_legacy_hook.sh')
LEGACY_HOOK_BASE_PATH = '/usr/share/ucs-school-import/hooks'
RESULTFILE = '/tmp/test82_result.txt'
EXPECTED_CLASSES = [
	'AnyComputer', 'AnyDHCPService', 'BasicGroup', 'BasicSchoolGroup', 'ClassShare', 'ComputerRoom', 'Container',
	'DHCPDNSPolicy', 'DHCPServer', 'DHCPService', 'DHCPSubnet', 'DNSReverseZone', 'ExamStudent', 'Group', 'ImportStaff',
	'ImportStudent', 'ImportTeacher', 'ImportTeachersAndStaff', 'ImportUser', 'IPComputer', 'LegacyImportStaff',
	'LegacyImportStudent', 'LegacyImportTeacher', 'LegacyImportTeachersAndStaff', 'LegacyImportUser', 'MacComputer',
	'MailDomain', 'Network', 'OU', 'Policy', 'School', 'SchoolClass', 'SchoolComputer', 'SchoolDC', 'SchoolDCSlave',
	'SchoolGroup', 'Share', 'Staff', 'Student', 'Teacher', 'TeachersAndStaff', 'UCCComputer', 'UMCPolicy', 'User',
	'WindowsComputer', 'WorkGroup', 'WorkGroupShare'
]

logger = get_ucsschool_logger()


def get_ucsschool_model_classes():
	# Will not find "printer" and "router" as they are not implemented in
	# ucsschool.lib.models, only in the legacy-import.
	classes = []
	for path, package in MODULE_PATHS:
		logger.info('Looking for subclass of %r in %r...', BASE_CLASS.__name__, path)
		for filename in os.listdir(path):
			if filename.endswith('.py'):
				module = importlib.import_module('{}.{}'.format(package, filename[:-3]))
				mod_classes = []
				for thing in dir(module):
					candidate = getattr(module, thing)
					if (
							inspect.isclass(candidate) and
							issubclass(candidate, BASE_CLASS) and
							candidate is not BASE_CLASS
					):
						mod_classes.append(candidate)
				logger.debug('Found in %r: %r.', filename, [c.__name__ for c in mod_classes])
				classes.extend(mod_classes)
	res = sorted(set(classes), key=lambda x: x.__name__.lower())
	logger.info('Loaded %d classes: %r.', len(res), [c.__name__ for c in res])
	return res


def check_lines_for_pattern_and_words(lines, pattern, *words):
	regex = re.compile(pattern)
	for line in lines:
		if regex.match(line) and all(word in line for word in words):
			return True
	return False


class TestLegacyHooksMeta(type):
	def __new__(mcls, cls_name, bases, attrs):
		logger.debug('Creating test methods...')
		cls = super(TestLegacyHooksMeta, mcls).__new__(mcls, cls_name, bases, attrs)  # type: Type[TestLegacyHooks]
		cls.models = get_ucsschool_model_classes()
		cls.func2model = {}
		school_base_abc_source = inspect.getsourcelines(UCSSchoolHelperAbstractClass.build_hook_line)
		for model in cls.models:
			if (
					inspect.getsourcelines(model.build_hook_line) == school_base_abc_source or
					inspect.getsourcelines(model.build_hook_line)[0][-1].strip() == 'return None'
			):
				logger.debug('Model %r does not support legacy hooks, skipping.', model.__name__)
				continue
			if model.__name__ in ('ImportUser', 'LegacyImportUser',  'SchoolComputer', 'UCCComputer', 'User'):
				logger.debug('Model %r not meant to be used directly, skipping.', model.__name__)
				continue
			for action, func in (
					('create', cls._test_create),
					('modify', cls._test_modify),
					('move', cls._test_move),
					('remove', cls._test_remove)
			):
				# luckily the functions names sort alphabetically in just the right order
				method_name = 'test_{}_{}'.format(model.__name__, action)
				setattr(cls, method_name, func)
				cls.func2model[method_name] = model
				logger.debug('Created method %r.', method_name)
		logger.debug('Created %d test methods.', len(cls.func2model))
		return cls


class TestLegacyHooks(TestCase):
	ucs_test_school = None
	lo = None
	models = None  # populated in metaclass
	methods = ('create', 'modify', 'move', 'remove')
	times = ('pre', 'post')
	objects = {}
	ou_name = ou_dn = None
	ou2_name = ou2_dn = None
	import_config = None
	progress_counter = 0

	__metaclass__ = TestLegacyHooksMeta

	@classmethod
	def setUpClass(cls):
		cls.ucs_test_school = UCSTestSchool()
		cls.lo = cls.ucs_test_school.lo
		(cls.ou_name, cls.ou_dn), (cls.ou2_name, cls.ou2_dn) = cls.ucs_test_school.create_multiple_ous(2)
		logger.info('Using OUs %r and %r.', cls.ou_name, cls.ou2_name)

	@classmethod
	def tearDownClass(cls):
		cls.ucs_test_school.cleanup()
		try:
			os.remove(RESULTFILE)
		except OSError:
			pass

	def setUp(self):
		self._created_dirs = []
		self._created_hooks = []
		with open(RESULTFILE, 'w') as fp:
			fp.truncate()
		test_method_name = self.id().rsplit('.', 1)[-1]  # 'test_ComputerRoom_create'
		if test_method_name == 'test_000_classes':
			return
		self.operation_name = test_method_name.rsplit('_', 1)[-1]  # 'create'
		self.model = self.func2model[test_method_name]  # <class ComputerRoom>
		try:
			self.hook_type = self.model.Meta.hook_path  # 'group'
		except AttributeError:
			self.hook_type = self.model.Meta.udm_module.split('/')[-1]  # 'group'
		logger.debug('setUp() %r (hook path: %r)', test_method_name, self.hook_type)  # create line break
		self.model._empty_hook_paths = set()
		self._created_dirs, all_dirs = self._create_hook_dirs(self.hook_type, self.operation_name)
		with open(TEST_HOOK_SOURCE, 'r') as fpr:
			hook_source_text = fpr.read()
		for _dir in all_dirs:
			hook_path = os.path.join(_dir, '82{}'.format(test_method_name))
			token = os.path.basename(_dir)
			with open(hook_path, 'w') as fpw:
				text = hook_source_text.format(TOKEN=token, TARGET_FILE=RESULTFILE)
				fpw.write(text)
				os.fchmod(fpw.fileno(), 0o755)
			logger.debug('Created %r.', hook_path)
			self._created_hooks.append(hook_path)

	def tearDown(self):
		for path in self._created_hooks:
			logger.debug('os.remove(%r)', path)
			os.remove(path)
		for path in self._created_dirs:
			logger.debug('os.rmdir(%r)', path)
			os.rmdir(path)

	def test_000_classes(self):
		self.assertSequenceEqual(
			[m.__name__ for m in self.models],
			EXPECTED_CLASSES,
			'Did not find the classes that were expected. Expected:\n{!r}\nGot:\n{!r}'.format(
				EXPECTED_CLASSES, self.models))

	@classmethod
	def _create_hook_dirs(cls, hook_type, method_name):
		all_dirs = []
		created_dirs = []
		for dir_name in ('{}_{}_{}.d'.format(hook_type.lower(), method_name, t) for t in cls.times):
			path = os.path.join(LEGACY_HOOK_BASE_PATH, dir_name)
			all_dirs.append(path)
			if not os.path.exists(path):
				logger.debug('os.mkdir(%r)', path)
				os.mkdir(path)
				created_dirs.append(path)
		return created_dirs, all_dirs

	def _check_test_setup(self):
		for _dir in ('{}_{}_{}.d'.format(self.hook_type, self.operation_name, t) for t in self.times):
			hook_file_path = os.path.join(LEGACY_HOOK_BASE_PATH, _dir)
			self.assertTrue(os.path.isdir(hook_file_path), 'Not a / not existing dir: {!r}'.format(hook_file_path))
		with open(RESULTFILE, 'r') as fp:
			self.assertEqual(len(fp.read()), 0, 'Result file {!r} is not empty.'.format(RESULTFILE))
		self.assertSetEqual(self.model._empty_hook_paths, set())

	def _test_create(self):
		self.__class__.progress_counter += 1
		logger.info(
			'** Test %d/%d create() of model %r...',
			self.progress_counter, len(self.func2model), self.model.__name__)
		self._check_test_setup()

		try:
			obj = getattr(self, '_setup_{}'.format(self.model.__name__))()
		except AttributeError:
			name = uts.random_username()
			obj = self.model(school=self.ou_name, name=name)
		logger.debug('Creating %s object with name %r in school %r...', self.model.__name__, obj.name, self.ou_name)
		obj.create(self.lo)
		with open(RESULTFILE, 'r') as fp:
			txt = fp.read()
		logger.debug('Content of result file: ---\n%s\n---', txt)
		if self.model.__name__ == 'School':
			patterns_and_words = (
				(r'^{}_create_pre.d'.format(self.hook_type), (obj.name,)),
				(r'^{}_create_post.d'.format(self.hook_type), (obj.name,))
			)
		else:
			patterns_and_words = (
				(r'^{}_create_pre.d'.format(self.hook_type), (self.ou_name, obj.name)),
				(r'^{}_create_post.d'.format(self.hook_type), (self.ou_name, obj.name))
			)
		for pattern, words in patterns_and_words:
			self.assertTrue(
				check_lines_for_pattern_and_words(txt.split('\n'), pattern, *words),
				'Could not find expected pattern {!r} and words {!r} in result file: ---\n{}\n---'.format(
					pattern, words, txt.strip())
			)

		self.objects[self.model] = obj
		logger.info('** OK %d/%d create() of model %r.', self.progress_counter, len(self.func2model),
					self.model.__name__)

	def _test_modify(self):
		self.__class__.progress_counter += 1
		logger.info(
			'** Test %d/%d modify() of model %r...',
			self.progress_counter, len(self.func2model), self.model.__name__)
		self._check_test_setup()

		try:
			obj = self.objects[self.model]
		except KeyError:
			raise KeyError('No object found for class {!r}. Probably create() failed.'.format(self.model.__name__))
		# try to change an attribute, not that it'd be necessary, but it can't hurt either
		if hasattr(obj, 'display_name'):
			obj.display_name = uts.random_name()
		elif hasattr(obj, 'description'):
			obj.description = uts.random_name()
		elif hasattr(obj, 'inventory_number'):
			obj.inventory_number = uts.random_name()
		elif hasattr(obj, 'firstname'):
			obj.firstname = uts.random_name()
		obj.modify(self.lo)
		with open(RESULTFILE, 'r') as fp:
			txt = fp.read()
		logger.debug('Content of result file: ---\n%s\n---', txt)
		if self.model is School:
			logger.info('Model School does not support modify hooks.')
			patterns_and_words = ((r'^$', ()),)
		elif issubclass(self.model, Group):
			logger.warn('Model %r does not support modify hooks, if obj.name does not change.', self.model.__name__)
			# TODO: this might be a bug, investigate.
			patterns_and_words = ((r'^$', ()),)
		else:
			patterns_and_words = (
				(r'^{}_modify_pre.d'.format(self.hook_type), (self.ou_name, obj.name)),
				(r'^{}_modify_post.d'.format(self.hook_type), (self.ou_name, obj.name))
			)
		for pattern, words in patterns_and_words:
			self.assertTrue(
				check_lines_for_pattern_and_words(txt.split('\n'), pattern, *words),
				'Could not find expected pattern {!r} and words {!r} in result file: ---\n{}\n---'.format(
					pattern, words, txt.strip())
			)
		logger.info('** OK %d/%d modify() of model %r.', self.progress_counter, len(self.func2model),
					self.model.__name__)

	def _test_move(self):
		self.__class__.progress_counter += 1
		logger.info(
			'** Test %d/%d move() of model %r from OU %r to %r ...',
			self.progress_counter, len(self.func2model), self.model.__name__, self.ou_name, self.ou2_name)
		self._check_test_setup()

		try:
			obj = self.objects[self.model]
		except KeyError:
			raise KeyError('No object found for class {!r}. Probably create() failed.'.format(self.model.__name__))
		if hasattr(obj, 'schools'):
			obj.change_school(self.ou2_name, self.lo)
		else:
			obj.school = self.ou2_name
			# the move will fail - that's expected - see patterns_and_words below
			self.assertFalse(obj.move(self.lo), 'Move of {!r} model succeeded unexpectedly.'.format(self.model.__name__))
			obj.school = self.ou_name

		with open(RESULTFILE, 'r') as fp:
			txt = fp.read()
		logger.debug('Content of result file: ---\n%s\n---', txt)
		if self.model is School:
			logger.info('Model School does not support move hooks.')
			patterns_and_words = ((r'^$', ()),)
		elif self.model._meta.allow_school_change:
			patterns_and_words = (
				(r'^{}_move_pre.d'.format(self.hook_type), (self.ou2_name, obj.name)),
				(r'^{}_move_post.d'.format(self.hook_type), (self.ou2_name, obj.name))
			)
		else:
			# move operation failed, post hook won't be executed
			patterns_and_words = (
				(r'^{}_move_pre.d'.format(self.hook_type), (obj.name,)),
			)
		for pattern, words in patterns_and_words:
			self.assertTrue(
				check_lines_for_pattern_and_words(txt.split('\n'), pattern, *words),
				'Could not find expected pattern {!r} and words {!r} in result file: ---\n{}\n---'.format(
					pattern, words, txt.strip())
			)
		logger.info('** OK %d/%d move() of model %r.', self.progress_counter, len(self.func2model), self.model.__name__)

	def _test_remove(self):
		self.__class__.progress_counter += 1
		logger.info(
			'** Test %d/%d remove() of model %d/%d: %r...',
			self.progress_counter, len(self.func2model), self.model.__name__)
		self._check_test_setup()

		if self.model is School:
			# ldapError: Operation not allowed on non-leaf: subordinate objects must be deleted first
			logger.info('Model School does not support "remove" method.')
			return

		try:
			obj = self.objects[self.model]
		except KeyError:
			raise KeyError('No object found for class {!r}. Probably create() failed.'.format(self.model.__name__))
		obj.remove(self.lo)
		with open(RESULTFILE, 'r') as fp:
			txt = fp.read()
		logger.debug('Content of result file: ---\n%s\n---', txt)
		patterns_and_words = (
			(r'^{}_remove_pre.d'.format(self.hook_type), (obj.school, obj.name)),
			(r'^{}_remove_post.d'.format(self.hook_type), (obj.school, obj.name))
		)
		for pattern, words in patterns_and_words:
			self.assertTrue(
				check_lines_for_pattern_and_words(txt.split('\n'), pattern, *words),
				'Could not find expected pattern {!r} and words {!r} in result file: ---\n{}\n---'.format(
					pattern, words, txt.strip())
			)
		logger.info('** OK %d/%d remove() of model %r.', self.progress_counter, len(self.func2model), self.model.__name__)

	def _setup_ExamStudent(self):
		return self.model(
			school=self.ou_name,
			name=uts.random_username(),
			firstname=uts.random_username(),
			lastname=uts.random_username(),
		)
	_setup_Staff = _setup_ExamStudent
	_setup_Student = _setup_ExamStudent
	_setup_Teacher = _setup_ExamStudent
	_setup_TeachersAndStaff = _setup_ExamStudent

	def _setup_School(self):
		return self.model(
			name=uts.random_username(),
		)

	def _setup_IPComputer(self):
		return self.model(
			school=self.ou_name,
			name=uts.random_username(),
			ip_address=[random_ip()],
			mac_address=[random_mac()],
		)
	_setup_MacComputer = _setup_IPComputer
	_setup_WindowsComputer = _setup_IPComputer

	@classmethod
	def _setup_import_framework(cls):
		if cls.import_config:
			return
		logger.info('Setting up import framework...')
		import_config_args = {
			'dry_run': False,
			'source_uid': 'TestDB',
			'verbose': True
		}
		ui = UserImportCommandLine()
		config_files = ui.configuration_files
		cls.import_config = setup_configuration(config_files, **import_config_args)
		# ui.setup_logging(cls.import_config['verbose'], cls.import_config['logfile'])
		setup_factory(cls.import_config['factory'])
		logger.info("------ UCS@school import tool configured ------")
		logger.info("Used configuration files: %s.", cls.import_config.conffiles)
		logger.info("Using command line arguments: %r", import_config_args)
		logger.info("Configuration is:\n%s", pprint.pformat(cls.import_config))

	def _setup_ImportStaff(self):
		self._setup_import_framework()
		return self.model(
			school=self.ou_name,
			name=uts.random_username(),
			firstname=uts.random_username(),
			lastname=uts.random_username(),
			source_uid=self.import_config['source_uid'],
			record_uid=uts.random_username(),
		)
	_setup_ImportStudent = _setup_ImportStaff
	_setup_ImportTeacher = _setup_ImportStaff
	_setup_ImportTeachersAndStaff = _setup_ImportStaff
	_setup_LegacyImportStaff = _setup_ImportStaff
	_setup_LegacyImportStudent = _setup_ImportStaff
	_setup_LegacyImportTeacher = _setup_ImportStaff
	_setup_LegacyImportTeachersAndStaff = _setup_ImportStaff


if __name__ == '__main__':
	main(verbosity=2)
