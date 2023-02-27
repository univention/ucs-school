#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: Test execution of Python based hooks
## exposure: dangerous
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## packages: [python3-ucsschool-lib, ucs-school-import]
## bugs: [49557]

import importlib
import inspect
import os
import os.path
import pprint
import random
import re
from unittest import TestCase, main

from six import PY3, add_metaclass

import ucsschool.lib.models.user
import univention.testing.strings as uts
from ucsschool.importer.configuration import setup_configuration
from ucsschool.importer.factory import setup_factory
from ucsschool.importer.frontend.user_import_cmdline import UserImportCommandLine
from ucsschool.lib.models.base import PYHOOKS_PATH, UCSSchoolHelperAbstractClass, _pyhook_loader
from ucsschool.lib.models.dhcp import DHCPService
from ucsschool.lib.models.group import Group, SchoolClass, WorkGroup
from ucsschool.lib.models.school import School
from univention.testing.ucsschool.computer import random_ip, random_mac
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool, get_ucsschool_logger

py = "3" if PY3 else "2.7"

MODULE_PATHS = (
    ("/usr/lib/python%s/dist-packages/ucsschool/lib/models" % (py,), "ucsschool.lib.models"),
    ("/usr/lib/python%s/dist-packages/ucsschool/importer/models" % (py,), "ucsschool.importer.models"),
)
BASE_CLASS = UCSSchoolHelperAbstractClass
TEST_HOOK_SOURCE = os.path.join(os.path.dirname(__file__), "test83_python_hookpy")
RESULTFILE = "/tmp/test83_result.txt"
EXPECTED_CLASSES = {
    "AnyComputer": "ucsschool.lib.models.computer",
    "AnyDHCPService": "ucsschool.lib.models.dhcp",
    "BasicGroup": "ucsschool.lib.models.group",
    "BasicSchoolGroup": "ucsschool.lib.models.group",
    "ClassShare": "ucsschool.lib.models.share",
    "ComputerRoom": "ucsschool.lib.models.group",
    "Container": "ucsschool.lib.models.misc",
    "DHCPDNSPolicy": "ucsschool.lib.models.policy",
    "DHCPServer": "ucsschool.lib.models.dhcp",
    "DHCPService": "ucsschool.lib.models.dhcp",
    "DHCPSubnet": "ucsschool.lib.models.dhcp",
    "DNSReverseZone": "ucsschool.lib.models.network",
    "ExamStudent": "ucsschool.lib.models.user",
    "Group": "ucsschool.lib.models.group",
    "GroupShare": "ucsschool.lib.models.share",
    "IPComputer": "ucsschool.lib.models.computer",
    "ImportStaff": "ucsschool.importer.models.import_user",
    "ImportStudent": "ucsschool.importer.models.import_user",
    "ImportTeacher": "ucsschool.importer.models.import_user",
    "ImportTeachersAndStaff": "ucsschool.importer.models.import_user",
    "ImportUser": "ucsschool.importer.models.import_user",
    "LinuxComputer": "ucsschool.lib.models.computer",
    "MacComputer": "ucsschool.lib.models.computer",
    "MailDomain": "ucsschool.lib.models.misc",
    "MarketplaceShare": "ucsschool.lib.models.share",
    "Network": "ucsschool.lib.models.network",
    "OU": "ucsschool.lib.models.misc",
    "Policy": "ucsschool.lib.models.policy",
    "School": "ucsschool.lib.models.school",
    "SchoolAdmin": "ucsschool.lib.models.user",
    "SchoolClass": "ucsschool.lib.models.group",
    "SchoolComputer": "ucsschool.lib.models.computer",
    "SchoolDC": "ucsschool.lib.models.computer",
    "SchoolDCSlave": "ucsschool.lib.models.computer",
    "SchoolGroup": "ucsschool.lib.models.group",
    "Share": "ucsschool.lib.models.share",
    "Staff": "ucsschool.lib.models.user",
    "Student": "ucsschool.lib.models.user",
    "Teacher": "ucsschool.lib.models.user",
    "TeachersAndStaff": "ucsschool.lib.models.user",
    "UbuntuComputer": "ucsschool.lib.models.computer",
    "UMCPolicy": "ucsschool.lib.models.policy",
    "User": "ucsschool.lib.models.user",
    "WindowsComputer": "ucsschool.lib.models.computer",
    "WorkGroup": "ucsschool.lib.models.group",
    "WorkGroupShare": "ucsschool.lib.models.share",
}
CLASSES_WITH_SCHOOL_NONE = ("AnyDHCPService", "BasicGroup", "MailDomain", "DNSReverseZone", "School")
# base classes meant for subclassing:
CLASSES_NOT_FOR_INSTANTIATION = (
    "AnyComputer",
    "BasicSchoolGroup",
    "ImportUser",
    "SchoolComputer",
    "Share",
    "User",
)

logger = get_ucsschool_logger()


def get_ucsschool_model_classes():
    # Will not find "printer" and "router" as they are not implemented in
    # ucsschool.lib.models, only in the legacy-import.
    classes = []
    for path, package in MODULE_PATHS:
        logger.info("Looking for subclass of %r in %r...", BASE_CLASS.__name__, path)
        for filename in os.listdir(path):
            if filename.endswith(".py"):
                module = importlib.import_module("{}.{}".format(package, filename[:-3]))
                mod_classes = []
                for thing in dir(module):
                    candidate = getattr(module, thing)
                    if (
                        inspect.isclass(candidate)
                        and issubclass(candidate, BASE_CLASS)
                        and candidate is not BASE_CLASS
                    ):
                        mod_classes.append(candidate)
                logger.debug("Found in %r: %r.", filename, [c.__name__ for c in mod_classes])
                classes.extend(mod_classes)
    res = sorted(set(classes), key=lambda x: x.__name__.lower())
    logger.info("Loaded %d classes: %r.", len(res), [c.__name__ for c in res])
    return res


def check_lines_for_pattern_and_words(lines, pattern, *words):
    regex = re.compile(pattern)
    for line in lines:
        if regex.match(line) and all(str(word) in line for word in words):
            return True
    return False


class TestPythonHooksMeta(type):
    def __new__(mcls, cls_name, bases, attrs):
        logger.debug("Creating test methods...")
        cls = super(TestPythonHooksMeta, mcls).__new__(
            mcls, cls_name, bases, attrs
        )  # type: TestPythonHooks
        models = get_ucsschool_model_classes()
        cls.func2model = {}
        cls.ignored_classes = list(CLASSES_NOT_FOR_INSTANTIATION)
        for model in models:
            if not hasattr(model, "Meta"):
                # skip base classes without a "Meta" class: Policy, SchoolDC
                logger.info('Model %r without inner class "Meta", skipping.', model.__name__)
                cls.ignored_classes.append(model.__name__)
                continue
            if model.__name__ in cls.ignored_classes:
                # skip base classes with a "Meta" class
                logger.info("Model %r not meant to be used directly, skipping.", model.__name__)
                continue
            cls.models.append(model)
            for action, func in (
                ("create", cls._test_create),
                ("modify", cls._test_modify),
                ("move", cls._test_move),
                ("remove", cls._test_remove),
            ):
                # luckily the functions names sort alphabetically in just the right order
                method_name = "test_{}_{}".format(model.__name__, action)
                setattr(cls, method_name, func)
                cls.func2model[method_name] = model
                logger.debug("Created method %r.", method_name)
        logger.debug("Created %d test methods.", len(cls.func2model))
        return cls


@add_metaclass(TestPythonHooksMeta)
class TestPythonHooks(TestCase):
    """This class is extended by the metaclass with >100 "test_Student_modify" methods."""

    ucs_test_school = None
    lo = None
    models = []  # populated in metaclass
    methods = ("create", "modify", "move", "remove")
    times = ("pre", "post")
    objects = {}
    ou_name = ou_dn = None
    ou2_name = ou2_dn = None
    import_config = None
    progress_counter = 0
    _created_hook = None
    _dhcp_service = None
    _import_line_class2module = {
        "ImportStaff": "ucsschool.importer.models.import_user",
        "ImportStudent": "ucsschool.importer.models.import_user",
        "ImportTeacher": "ucsschool.importer.models.import_user",
        "ImportTeachersAndStaff": "ucsschool.importer.models.import_user",
    }

    @classmethod
    def setUpClass(cls):
        cls.ucs_test_school = UCSTestSchool()
        cls.lo = cls.ucs_test_school.lo
        (cls.ou_name, cls.ou_dn), (cls.ou2_name, cls.ou2_dn) = cls.ucs_test_school.create_multiple_ous(2)
        logger.info("Using OUs %r and %r.", cls.ou_name, cls.ou2_name)
        assert cls.ou_name != cls.ou2_name

    @classmethod
    def tearDownClass(cls):
        if cls._dhcp_service:
            logger.debug("Removing object %r...", cls._dhcp_service)
            cls._dhcp_service.remove(cls.ucs_test_school.lo)
        cls.ucs_test_school.cleanup()
        try:
            os.remove(RESULTFILE)
        except OSError:
            pass
        cls._delete_hook(cls._created_hook)

    def setUp(self):
        self.__class__.progress_counter += 1
        test_method_name = self.id().rsplit(".", 1)[-1]  # 'test_ComputerRoom_create'
        logger.debug("setUp() %r", test_method_name)  # create line break
        logger.info(
            "#################  %s (%d/%d)  #################",
            test_method_name,
            self.progress_counter,
            len(self.func2model) + 2,
        )
        with open(RESULTFILE, "w") as fp:
            fp.truncate()
        self._created_lib_objects = []
        if test_method_name == "test_001_all_known_classes":
            # no hook file needs to be created for this test
            self.operation_name = ""
            return
        elif test_method_name == "test_002_subclassing":
            # set a value so the following code can create the required hook file with "model = Teacher"
            test_method_name = "test_Teacher_create"
        self.operation_name = test_method_name.rsplit("_", 1)[-1]  # 'create'
        self.model = self.func2model[test_method_name]  # <class ComputerRoom>
        if self.operation_name == "create":
            # create hook only once per class, as it contains code for
            # all of (pre, post) x (create, modify, move, remove)
            _pyhook_loader.drop_cache()
            with open(TEST_HOOK_SOURCE) as fpr:
                hook_source_text = fpr.read()
            hook_file_path = os.path.join(
                PYHOOKS_PATH, "test83_{}_hook.py".format(self.model.__name__.lower())
            )
            try:
                imp_txt = "from {} import {}".format(
                    self._import_line_class2module[self.model.__name__], self.model.__name__
                )
            except KeyError:
                imp_txt = "from {} import {}".format(
                    EXPECTED_CLASSES[self.model.__name__], self.model.__name__
                )
            with open(hook_file_path, "w") as fpw:
                text = (
                    hook_source_text.replace("MODEL_CLASS_VAR", self.model.__name__)
                    .replace("TARGET_FILE_VAR", RESULTFILE)
                    .replace("IMPORT_VAR", imp_txt)
                )
                fpw.write(text)
            self.__class__._created_hook = hook_file_path
            logger.info("Created %r.", hook_file_path)

    def tearDown(self):
        for obj in self._created_lib_objects:
            logger.debug("Removing object %r...", obj)
            obj.remove(self.lo)
        # remove hook only once per model, as it contains code for
        # all of (pre, post) x (create, modify, move, remove):
        if self.operation_name == "remove":
            self._delete_hook(self._created_hook)

    @staticmethod
    def _delete_hook(path):
        for pat in (path, path + "c"):
            try:
                os.remove(pat)
                logger.info("Deleted %r.", pat)
            except OSError:
                pass

    def test_001_all_known_classes(self):
        model_names = sorted([m.__name__ for m in self.models] + self.ignored_classes)
        diff = set(model_names).symmetric_difference(set(EXPECTED_CLASSES.keys()))
        self.assertSequenceEqual(
            model_names,
            sorted(EXPECTED_CLASSES.keys()),
            "=====> Did not find the classes that were expected. Expected:\n{!r}\nGot:\n{!r}\n"
            "Diff: {!r}".format(list(EXPECTED_CLASSES.keys()), model_names, sorted(diff)),
        )

    def test_002_subclassing(self):
        # setUp() has created a hook for "Teacher"
        # now create Student, Teacher and TeachersAndStaff objects
        # hooks are expected to run for Teacher and TeachersAndStaff
        self._check_test_setup()
        patterns_and_words = []
        for klass in ("Staff", "Student", "Teacher", "TeachersAndStaff"):
            self.model = getattr(ucsschool.lib.models.user, klass)
            obj = getattr(self, "_create_{}".format(klass))()
            words = klass, obj.name, obj.school
            logger.debug("** Creating %s object with name %r in school %r...", *words)  # noqa: PLE1206
            obj.create(self.lo)
            if klass not in ("Staff", "Student"):
                patterns_and_words.extend([(r"^pre_create", words), (r"^post_create", words)])
        with open(RESULTFILE) as fp:
            txt = fp.read()
        logger.debug("Content of result file: ---\n%s\n---", txt)
        for pattern, words in patterns_and_words:
            assert check_lines_for_pattern_and_words(txt.split("\n"), pattern, *words)

    def _check_test_setup(self):
        hook_file_path = os.path.join(
            PYHOOKS_PATH, "test83_{}_hook.py".format(self.model.__name__.lower())
        )
        assert os.path.isfile(hook_file_path)
        with open(RESULTFILE) as fp:
            assert len(fp.read()) == 0

    def _test_create(self):
        logger.info(
            "** Test %d/%d create() of model %r...",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )
        self._check_test_setup()

        try:
            obj = getattr(self, "_create_{}".format(self.model.__name__))()
        except AttributeError:
            name = uts.random_username()
            obj = self.model(school=self.ou_name, name=name)
        logger.debug(
            "Creating %s object with name %r in school %r...",
            self.model.__name__,
            obj.name,
            self.ou_name,
        )
        obj.create(self.lo)
        with open(RESULTFILE) as fp:
            txt = fp.read()
        logger.debug("Content of result file: ---\n%s\n---", txt)
        if self.model.__name__ in CLASSES_WITH_SCHOOL_NONE:
            # hard coded: school = None
            patterns_and_words = (
                (r"^pre_create", (obj.__class__.__name__, obj.name, "None")),
                (r"^post_create", (obj.__class__.__name__, obj.name, "None")),
            )
        else:
            # pre_create MacComputer w7pe5ki4in DEMOSCHOOL
            patterns_and_words = (
                (r"^pre_create", (obj.__class__.__name__, obj.name, obj.school)),
                (r"^post_create", (obj.__class__.__name__, obj.name, obj.school)),
            )
        for pattern, words in patterns_and_words:
            assert check_lines_for_pattern_and_words(txt.split("\n"), pattern, *words)

        self.objects[self.model] = obj  # save object for next test function (_test_modify)
        logger.info(
            "** OK %d/%d create() of model %r.\n------------------------------------------------------",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )

    def _test_modify(self):
        logger.info(
            "** Test %d/%d modify() of model %r...",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )
        self._check_test_setup()

        if self.model.__name__ in ("Container", "OU"):
            logger.info("Model {!r} does not support modify() method.".format(self.model.__name__))
            return
        try:
            obj = self.objects[self.model]
        except KeyError:
            raise KeyError(
                "No object found for class {!r}. Probably create() failed.".format(self.model.__name__)
            )
        # try to change an attribute, not that it'd be necessary, but it can't hurt either
        if hasattr(obj, "display_name"):
            obj.display_name = uts.random_name()
        elif hasattr(obj, "description"):
            obj.description = uts.random_name()
        elif hasattr(obj, "inventory_number"):
            obj.inventory_number = uts.random_name()
        elif hasattr(obj, "firstname"):
            obj.firstname = uts.random_name()
        elif obj.__class__.__name__ == "DHCPServer":
            obj.name = "{}b".format(obj.name)  # change something
            obj.dhcp_service = self._dhcp_service  # not loaded automatically, but required
        elif obj.__class__.__name__ == "Network":
            obj.netmask = "21"  # prevent UDM valueMayNotChange exception (value is 255.255.248.0)
            obj.broadcast = "12.40.232.255"  # change something (was None)
        obj.modify(self.lo)
        with open(RESULTFILE) as fp:
            txt = fp.read()
        logger.debug("Content of result file:\n---\n%s---", txt)
        if self.model is School:
            logger.info("Model School does not support modify hooks.")
            patterns_and_words = ((r"^$", ()),)
        elif self.model.__name__ in CLASSES_WITH_SCHOOL_NONE:
            # hard coded: AnyDHCPService.school = None
            patterns_and_words = (
                (r"^pre_modify", (obj.__class__.__name__, obj.name, "None")),
                (r"^post_modify", (obj.__class__.__name__, obj.name, "None")),
            )
        elif issubclass(self.model, Group):
            logger.warning(
                "Model %r does not support modify hooks, if obj.name does not change.",
                self.model.__name__,
            )
            # TODO: this might be a bug, investigate.
            patterns_and_words = ((r"^$", ()),)
        else:
            patterns_and_words = (
                (r"^pre_modify", (obj.__class__.__name__, obj.name, self.ou_name)),
                (r"^post_modify", (obj.__class__.__name__, self.ou_name, obj.name)),
            )
        for pattern, words in patterns_and_words:
            assert check_lines_for_pattern_and_words(txt.split("\n"), pattern, *words)
        logger.info(
            "** OK %d/%d modify() of model %r.",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )

    def _test_move(self):
        logger.info(
            "** Test %d/%d move() of model %r from OU %r to %r ...",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
            self.ou_name,
            self.ou2_name,
        )
        self._check_test_setup()

        try:
            obj = self.objects[self.model]
        except KeyError:
            raise KeyError(
                "No object found for class {!r}. Probably create() failed.".format(self.model.__name__)
            )
        if hasattr(obj, "schools"):
            obj.change_school(self.ou2_name, self.lo)
            move_success = True
        else:
            obj.school = self.ou2_name
            # the move will fail - that's expected - see patterns_and_words below
            move_success = obj.move(self.lo)
            assert not move_success
            obj.school = self.ou_name

        with open(RESULTFILE) as fp:
            txt = fp.read()
        logger.debug("Content of result file: ---\n%s\n---", txt)
        if self.model is School:
            logger.info("Model School does not support move hooks.")
            patterns_and_words = ((r"^$", ()),)
        elif move_success:
            patterns_and_words = (
                (r"^pre_move", (obj.__class__.__name__, self.ou2_name, obj.name)),
                (r"^post_move", (obj.__class__.__name__, self.ou2_name, obj.name)),
            )
        else:
            # move operation failed, post hook won't be executed
            # this is expected for various models
            patterns_and_words = ((r"^pre_move", (obj.__class__.__name__, self.ou2_name, obj.name)),)
        for pattern, words in patterns_and_words:
            assert check_lines_for_pattern_and_words(txt.split("\n"), pattern, *words)
        logger.info(
            "** OK %d/%d move() of model %r.",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )

    def _test_remove(self):
        logger.info(
            "** Test %d/%d remove() of model %r...",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )
        self._check_test_setup()

        if self.model.__name__ in ("School", "Container", "OU"):
            logger.info("Model {!r} does not support remove() method.".format(self.model.__name__))
            return

        try:
            obj = self.objects[self.model]
        except KeyError:
            raise KeyError(
                "No object found for class {!r}. Probably create() failed.".format(self.model.__name__)
            )
        obj.remove(self.lo)
        with open(RESULTFILE) as fp:
            txt = fp.read()
        logger.debug("Content of result file: ---\n%s\n---", txt)
        patterns_and_words = (
            (r"^pre_remove", (obj.__class__.__name__, obj.school, obj.name)),
            (r"^post_remove", (obj.__class__.__name__, obj.school, obj.name)),
        )
        for pattern, words in patterns_and_words:
            assert check_lines_for_pattern_and_words(txt.split("\n"), pattern, *words)
        logger.info(
            "** OK %d/%d remove() of model %r.",
            self.progress_counter,
            len(self.func2model) + 2,
            self.model.__name__,
        )

    def _create_ExamStudent(self):
        return self.model(
            school=self.ou_name,
            name=uts.random_username(),
            firstname=uts.random_username(),
            lastname=uts.random_username(),
        )

    _create_SchoolAdmin = _create_ExamStudent
    _create_Staff = _create_ExamStudent
    _create_Student = _create_ExamStudent
    _create_Teacher = _create_ExamStudent
    _create_TeachersAndStaff = _create_ExamStudent

    def _create_School(self):
        return self.model(
            name=uts.random_username(),
        )

    def _create_IPComputer(self):
        return self.model(
            school=self.ou_name,
            name=uts.random_username(),
            ip_address=[random_ip()],
            mac_address=[random_mac()],
        )

    _create_MacComputer = _create_IPComputer
    _create_WindowsComputer = _create_IPComputer
    _create_LinuxComputer = _create_IPComputer
    _create_UbuntuComputer = _create_IPComputer

    def _create_Share(self):
        group_model = random.choice((SchoolClass, WorkGroup))
        logger.debug(
            "Creating a %r object for the [Class/Group/Workgroup]Share...", group_model.__name__
        )
        school_group = group_model(
            school=self.ou_name, name="{}-{}".format(self.ou_name, uts.random_username())
        )
        if not school_group.create(self.lo):
            raise RuntimeError("Failed to create school group required for [...]Share object.")
        self._created_lib_objects.append(school_group)
        logger.debug("Created %r for [...]Share.", school_group)
        # use different (random) name for ClassShare, as school_group will
        # have automatically created a ClassShare with its own name
        return self.model(
            school=self.ou_name,
            name=uts.random_username(),
            school_group=school_group,
        )

    _create_ClassShare = _create_Share
    _create_GroupShare = _create_Share
    _create_WorkGroupShare = _create_Share

    def _create_MarketplaceShare(self):
        # there can be only one MarketplaceShare, and the test OU already has one
        self.model(school=self.ou_name).remove(self.lo)
        return self.model(school=self.ou_name)

    def _create_Container_(self):
        # regular setup works, but the wait_for_drs_removal() in udm.cleanup()
        # always fails, so remove it before the cleanup manually (add it to
        # self._created_lib_objects)
        # TODO: investigate why this happens
        obj = self.model(
            school=self.ou_name,
            name=uts.random_username(),
        )
        self._created_lib_objects.append(obj)
        return obj

    def _create_DHCPServer(self):
        logger.debug("Creating a DHCPService object for the DHCPServer...")
        name = uts.random_username()
        self.__class__._dhcp_service = DHCPService(
            school=self.ou_name,
            name="{}d".format(name),
        )
        if not self.__class__._dhcp_service.create(self.lo):
            raise RuntimeError("Failed creating DHCPService required for DHCPServer object.")
        # not adding dhcp_service to self._created_lib_objects, as we need it in modify() as well
        return self.model(
            school=self.ou_name,
            name=name,
            dhcp_service=self.__class__._dhcp_service,
        )

    def _create_DHCPSubnet(self):
        return self.model(
            school=self.ou_name,
            name="11.40.232.0",
            dhcp_service=self.__class__._dhcp_service,
            subnet_mask="255.255.248.0",  # /21
        )

    def _create_DNSReverseZone(self):
        return self.model(
            school=self.ou_name,
            name=uts.random_ip().rsplit(".", 1)[0],
        )

    def _create_Network(self):
        return self.model(
            school=self.ou_name,
            name="12.40.232.0",
            netmask="255.255.248.0",
            network="12.40.232.0",
        )

    def _create_SchoolClass(self):
        return self.model(school=self.ou_name, name="{}-{}".format(self.ou_name, uts.random_username()))

    _create_ComputerRoom = _create_SchoolClass
    _create_SchoolGroup = _create_SchoolClass
    _create_WorkGroup = _create_SchoolClass

    @classmethod
    def _setup_import_framework(cls):
        if cls.import_config:
            return
        logger.info("Setting up import framework...")
        import_config_args = {"dry_run": False, "source_uid": "TestDB", "verbose": True}
        ui = UserImportCommandLine()
        config_files = ui.configuration_files
        cls.import_config = setup_configuration(config_files, **import_config_args)
        # ui.setup_logging(cls.import_config['verbose'], cls.import_config['logfile'])
        setup_factory(cls.import_config["factory"])
        logger.info("------ UCS@school import tool configured ------")
        logger.info("Used configuration files: %s.", cls.import_config.conffiles)
        logger.info("Using command line arguments: %r", import_config_args)
        logger.info("Configuration is:\n%s", pprint.pformat(cls.import_config))

    def _create_ImportStaff(self):
        self._setup_import_framework()
        return self.model(
            school=self.ou_name,
            name=uts.random_username(),
            firstname=uts.random_username(),
            lastname=uts.random_username(),
            source_uid=self.import_config["source_uid"],
            record_uid=uts.random_username(),
        )

    _create_ImportStudent = _create_ImportStaff
    _create_ImportTeacher = _create_ImportStaff
    _create_ImportTeachersAndStaff = _create_ImportStaff


if __name__ == "__main__":
    main(failfast=True, verbosity=2)
