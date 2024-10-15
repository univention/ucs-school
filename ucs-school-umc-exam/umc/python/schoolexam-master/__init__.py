#!/usr/bin/python3
#
# UCS@school UMC module schoolexam-master
#  UMC module delivering backend services for ucs-school-umc-exam
#
# Copyright 2013-2024 Univention GmbH
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
"""
UCS@school UMC module schoolexam-master
UMC module delivering backend services for ucs-school-umc-exam
"""

import datetime
import logging
import os
import os.path
import re
import traceback
from collections import defaultdict
from typing import Dict, List, Tuple  # noqa: F401

import ldap
from ldap.dn import escape_dn_chars, str2dn
from ldap.filter import filter_format
from six import iteritems

import univention.admin.modules
import univention.admin.uexceptions
import univention.debug as ud
import univention.udm
from ucsschool.exam.exam_user_pyhook import ExamUserPyHook
from ucsschool.importer.utils.import_pyhook import ImportPyHookLoader
from ucsschool.lib.models.base import MultipleObjectsError
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.lib.models.group import ComputerRoom
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import ExamStudent, Student
from ucsschool.lib.models.utils import (
    ModuleHandler,
    NotInstalled,
    UnknownPackage,
    add_module_logger_to_schoollib,
    get_package_version,
)
from ucsschool.lib.roles import (
    context_type_exam,
    create_ucsschool_role_string,
    get_role_info,
    role_exam_user,
    role_teacher_computer,
)
from ucsschool.lib.school_umc_base import SchoolBaseModule
from ucsschool.lib.school_umc_ldap_connection import ADMIN_WRITE, USER_READ, LDAP_Connection
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import DNSanitizer, ListSanitizer, StringSanitizer

_ = Translation("ucs-school-umc-exam-master").translate

CREATE_USER_PRE_HOOK_DIR = "/usr/share/ucs-school-exam-master/pyhooks/create_exam_user_pre/"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if "schoolexam" not in list(logger.handlers):
    _module_handler = ModuleHandler(udebug_facility=ud.MODULE)
    _module_handler.set_name("schoolexam")
    _formatter = logging.Formatter(fmt="%(funcName)s:%(lineno)d  %(message)s")
    _module_handler.setFormatter(_formatter)
    logger.addHandler(_module_handler)


class Instance(SchoolBaseModule):
    _pre_create_hooks = None
    _room_host_cache = {}
    _examUserContainerDN = {}

    def __init__(self):
        SchoolBaseModule.__init__(self)
        univention.admin.modules.update()
        self._log_package_version("ucs-school-umc-exam-master")
        self._examUserPrefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
        self._examGroupExcludeRegEx = None
        try:
            value = ucr.get("ucsschool/exam/group/ldap/blacklist/regex", "")
            if value.strip():
                self._examGroupExcludeRegEx = re.compile(value, re.I)
        except Exception as ex:
            logger.error(
                "Failed to get/compile regexp provided by ucsschool/exam/group/ldap/blacklist/regex: %s",
                ex,
            )

        # cache objects
        self._udm_modules = {}
        self._examGroup = None
        self.exam_user_pre_create_hooks = None

    @staticmethod
    def _log_package_version(package_name):  # type: (str) -> None
        try:
            logger.info(
                "Package %r installed in version %r.", package_name, get_package_version(package_name)
            )
        except (NotInstalled, UnknownPackage) as exc:
            logger.error("Error retrieving package verion: %s", exc)

    def examGroup(self, ldap_admin_write, ldap_position, school):
        """fetch the examGroup object, create it if missing"""
        if not self._examGroup:
            logger.info("school=%r", school)
            search_base = School.get_search_base(school)
            examGroup = search_base.examGroup
            examGroupName = search_base.examGroupName
            if "groups/group" in self._udm_modules:
                module_groups_group = self._udm_modules["groups/group"]
            else:
                module_groups_group = univention.admin.modules.get("groups/group")
                univention.admin.modules.init(ldap_admin_write, ldap_position, module_groups_group)
                self._udm_modules["groups/group"] = module_groups_group

            # Determine exam_group_dn
            try:
                ldap_filter = "(objectClass=univentionGroup)"
                ldap_admin_write.searchDn(ldap_filter, examGroup, scope="base")
                self._examGroup = module_groups_group.object(
                    None, ldap_admin_write, ldap_position, examGroup
                )
                # self._examGroup.create() # currently not necessary
            except univention.admin.uexceptions.noObject:
                try:
                    position = univention.admin.uldap.position(ldap_position.getBase())
                    position.setDn(ldap_admin_write.parentDn(examGroup))
                    self._examGroup = module_groups_group.object(None, ldap_admin_write, position)
                    self._examGroup.open()
                    self._examGroup["name"] = examGroupName
                    self._examGroup["sambaGroupType"] = self._examGroup.descriptions[
                        "sambaGroupType"
                    ].base_default[0]
                    self._examGroup.create()
                except univention.admin.uexceptions.base:
                    raise UMC_Error(_("Failed to create exam group\n%s") % traceback.format_exc())

        return self._examGroup

    def examUserContainerDN(self, ldap_admin_write, ldap_position, school):
        """lookup examUserContainerDN, create it if missing"""
        if school not in self._examUserContainerDN:
            search_base = School.get_search_base(school)
            examUsers = search_base.examUsers
            examUserContainerName = search_base._examUserContainerName
            try:
                ldap_admin_write.searchDn("(objectClass=organizationalRole)", examUsers, scope="base")
            except univention.admin.uexceptions.noObject:
                try:
                    module_containers_cn = univention.admin.modules.get("container/cn")
                    univention.admin.modules.init(ldap_admin_write, ldap_position, module_containers_cn)
                    position = univention.admin.uldap.position(ldap_position.getBase())
                    position.setDn(ldap_admin_write.parentDn(examUsers))
                    exam_user_container = module_containers_cn.object(None, ldap_admin_write, position)
                    exam_user_container.open()
                    exam_user_container["name"] = examUserContainerName
                    exam_user_container.create()
                except univention.admin.uexceptions.base:
                    raise UMC_Error(_("Failed to create exam container\n%s") % traceback.format_exc())

            self._examUserContainerDN[school] = examUsers

        return self._examUserContainerDN[school]

    @sanitize(
        userdn=StringSanitizer(required=True),
        room=StringSanitizer(default=""),
        description=StringSanitizer(default=""),
        school=StringSanitizer(default=""),
        exam=StringSanitizer(default=""),
    )
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def create_exam_user(self, request, ldap_user_read=None, ldap_admin_write=None, ldap_position=None):
        """
        Create an exam account cloned from a given user account.
        The exam account is added to a special exam group to allow GPOs and other restrictions
        to be enforced via the name of this group.
        The group has to be created earlier, e.g. by create_ou (ucs-school-import).
        This function also restricts the login of the original user
        """
        school = request.options["school"]
        userdn = request.options["userdn"]
        room_dn = request.options["room"]
        exam = request.options["exam"]
        logger.info(
            "school=%r userdn=%r room=%r description=%r",
            school,
            userdn,
            room_dn,
            request.options["description"],
        )
        try:
            user = Student.from_dn(userdn, None, ldap_admin_write)
        except univention.admin.uexceptions.noObject:
            raise UMC_Error(_("Student %r not found.") % (userdn,))
        except univention.admin.uexceptions.ldapError:
            raise
        room = None
        if room_dn != "":
            try:
                room = ComputerRoom.from_dn(room_dn, None, ldap_user_read)
            except univention.admin.uexceptions.noObject:
                raise UMC_Error("Room %r not found." % (room_dn,))

        user_orig = user.get_udm_object(ldap_admin_write)

        if user_orig["disabled"] == "1":
            logger.info("Ignored disabled user {}".format(userdn))
            self.finished(request.id, None)
            return

        if len(user_orig["sambaUserWorkstations"]) == 0:
            user_orig["sambaUserWorkstations"] = ["$"]
        else:
            new_value = []
            for ws in user_orig["sambaUserWorkstations"]:
                new_ws = ws if ws.startswith("$") else "${}".format(ws)
                new_value.append(new_ws)
            user_orig["sambaUserWorkstations"] = new_value

        # disable original user
        if ucr.is_true("ucsschool/exam/user/disable"):
            logger.info("Disable original user {} temporarily.".format(userdn))
            user_orig["disabled"] = True
        user_orig.modify()

        # uid and DN of exam_user
        exam_user_uid = "".join((self._examUserPrefix, user_orig["username"]))
        exam_user_dn = "uid=%s,%s" % (
            escape_dn_chars(exam_user_uid),
            self.examUserContainerDN(ldap_admin_write, ldap_position, user.school or school),
        )

        try:
            exam_user = ExamStudent.get_only_udm_obj(
                ldap_admin_write, filter_format("uid=%s", (exam_user_uid,))
            )
            if exam_user is None:
                raise univention.admin.uexceptions.noObject(exam_user_uid)
            exam_user = ExamStudent.from_udm_obj(exam_user, None, ldap_admin_write)
        except (univention.admin.uexceptions.noObject, MultipleObjectsError):
            pass  # we need to create the exam user
        else:
            logger.warning("The exam account does already exist for: %r", exam_user_uid)
            if school not in exam_user.schools:
                exam_user.schools.append(school)
            role_str = create_ucsschool_role_string(
                role_exam_user, "{}-{}".format(exam, school), context_type_exam
            )
            if role_str not in exam_user.ucsschool_roles:
                exam_user.ucsschool_roles.append(role_str)
                exam_user.modify(ldap_admin_write)
            else:
                logger.warning(
                    "The exam user %r already participates in the exam %r. Do not add role.",
                    exam_user.name,
                    exam,
                )
            self.finished(request.id, {"success": True, "userdn": userdn, "examuserdn": exam_user.dn})
            return

        # Check if it's blacklisted
        for prohibited_object in univention.admin.handlers.settings.prohibited_username.lookup(
            None, ldap_admin_write, ""
        ):
            if exam_user_uid in prohibited_object["usernames"]:
                raise UMC_Error(
                    _(
                        "Requested exam username %(exam_user_uid)s is not allowed according to "
                        "settings/prohibited_username object %(prohibited_object_name)s"
                    )
                    % {
                        "exam_user_uid": exam_user_uid,
                        "prohibited_object_name": prohibited_object["name"],
                    }
                )

        # Allocate new uid
        alloc = []
        try:
            uid = univention.admin.allocators.request(
                ldap_admin_write, ldap_position, "uid", value=exam_user_uid
            )
            alloc.append(("uid", uid))
        except univention.admin.uexceptions.noLock:
            univention.admin.allocators.release(ldap_admin_write, ldap_position, "uid", exam_user_uid)
            logger.warning("The exam account does already exist for: %r", exam_user_uid)
            self.finished(
                request.id, {"success": True, "userdn": userdn, "examuserdn": exam_user_dn}, success=True
            )
            return

        # Ok, we have a valid target uid, so start cloning the user
        # deepcopy(user_orig) does not help much, as we cannot use users.user.object.create()
        # because it currently cannot be convinced to preserve the password. So we do it manually:
        try:
            # Allocate new uidNumber
            uidNum = univention.admin.allocators.request(ldap_admin_write, ldap_position, "uidNumber")
            alloc.append(("uidNumber", uidNum))

            # Allocate new sambaSID
            # code copied from users.user.object.__generate_user_sid:
            userSid = None
            if user_orig.s4connector_present:
                # In this case Samba 4 must create the SID, the s4 connector will sync the
                # new sambaSID back from Samba 4.
                userSid = "S-1-4-%s" % uidNum
            else:
                try:
                    userSid = univention.admin.allocators.requestUserSid(
                        ldap_admin_write, ldap_position, uidNum
                    )
                except (
                    ldap.LDAPError,
                    univention.admin.uexceptions.ldapError,
                    univention.admin.uexceptions.noLock,
                ):
                    pass
            if not userSid or userSid == "None":
                num = uidNum
                while not userSid or userSid == "None":
                    num = str(int(num) + 1)
                    try:
                        userSid = univention.admin.allocators.requestUserSid(
                            ldap_admin_write, ldap_position, num
                        )
                    except univention.admin.uexceptions.noLock:
                        num = str(int(num) + 1)
                alloc.append(("sid", userSid))

            # Determine description attribute for exam_user
            exam_user_description = request.options.get("description")
            if not exam_user_description:
                exam_user_description = _("Exam for user %s") % user_orig["username"]

            def getBlacklistSet(ucrvar):
                """
                >>> set([
                        x.replace('||','|')
                        for x in re.split('(?<![|])[|](?![|])', '|My|new|Value|with|Pipe||symbol')
                        if x
                    ])
                set(['with', 'new', 'My', 'Value', 'Pipe|symbol'])
                """
                return {
                    x.replace("||", "|")
                    for x in re.split("(?<![|])[|](?![|])", ucr.get(ucrvar, ""))
                    if x
                }

            blacklisted_attributes = getBlacklistSet("ucsschool/exam/user/ldap/blacklist")

            # Now create the addlist, fixing up attributes as we go
            al = []
            foundUniventionObjectFlag = False
            for key, value in user_orig.oldattr.items():
                # ignore blacklisted attributes
                if key in blacklisted_attributes:
                    continue
                # ignore operational attributes
                if key in (
                    "hasSubordinates",
                    "subschemaSubentry",
                    "entryDN",
                    "modifiersName",
                    "modifyTimestamp",
                    "entryCSN",
                    "memberOf",
                    "createTimestamp",
                    "creatorsName",
                    "entryUUID",
                    "structuralObjectClass",
                ):
                    continue
                if key == "sambaUserWorkstations":  # special handling for this attribute
                    continue
                # ignore blacklisted attribute values
                keyBlacklist = getBlacklistSet("ucsschool/exam/user/ldap/blacklist/%s" % key)
                value = [x for x in value if x not in keyBlacklist]
                if not value:
                    continue
                # handle special cases
                if key == "uid":
                    value = [exam_user_uid.encode("UTF-8")]
                elif key == "objectClass":
                    value += [b"ucsschoolExam"]
                elif key == "ucsschoolSchool" and school:
                    # for backwards compatibility with UCS@school < 4.1R2 school might not be set
                    if exam:
                        # for backwards compatibility with UCS@school prior Feb'20 exam might not be set
                        value = [s.encode("UTF-8") for s in user.schools]
                    else:
                        value = [school.encode("UTF-8")]
                elif key == "ucsschoolRole" and exam:
                    # for backwards compatibility with UCS@school prior Feb'20 exam might not be set
                    value = [
                        create_ucsschool_role_string(role_exam_user, s).encode("UTF-8")
                        for s in user.schools
                    ]
                    value.append(
                        create_ucsschool_role_string(
                            role_exam_user, "{}-{}".format(exam, school), context_type_exam
                        ).encode("UTF-8")
                    )
                elif key == "homeDirectory":
                    user_orig_homeDirectory = value[0].decode("UTF-8")
                    _tmp_split_path = user_orig_homeDirectory.rsplit(os.path.sep, 1)
                    if len(_tmp_split_path) != 2:
                        english_error_detail = "Failed parsing homeDirectory of original user: %s" % (
                            user_orig_homeDirectory,
                        )
                        message = _("ERROR: Creation of exam user account failed\n%s") % (
                            english_error_detail,
                        )
                        raise UMC_Error(message)
                    exam_user_unixhome = "%s.%s" % (
                        exam_user_uid,
                        datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
                    )
                    value = [
                        os.path.join(_tmp_split_path[0], "exam-homes", exam_user_unixhome).encode(
                            "UTF-8"
                        )
                    ]
                elif key == "sambaHomePath":
                    user_orig_sambaHomePath = value[0].decode("UTF-8")
                    value = [
                        user_orig_sambaHomePath.replace(user_orig["username"], exam_user_uid).encode(
                            "UTF-8"
                        )
                    ]
                elif key == "krb5PrincipalName":
                    user_orig_krb5PrincipalName = value[0].decode("UTF-8")
                    value = [
                        (
                            "%s%s"
                            % (
                                exam_user_uid,
                                user_orig_krb5PrincipalName[user_orig_krb5PrincipalName.find("@") :],
                            )
                        ).encode("UTF-8")
                    ]
                elif key == "uidNumber":
                    value = [uidNum.encode("UTF-8")]
                elif key == "sambaSID":
                    value = [userSid.encode("ASCII")]
                elif key == "description":
                    value = [exam_user_description.encode("UTF-8")]
                    exam_user_description = None  # that's done
                elif key == "univentionObjectFlag":
                    foundUniventionObjectFlag = True
                    if b"temporary" not in value:
                        value += [b"temporary"]
                al.append((key, value))
                if room:
                    if room not in self._room_host_cache:
                        self._room_host_cache[room] = room.get_computers(ldap_admin_write)
                    al.append(
                        (
                            "sambaUserWorkstations",
                            ",".join([c.name for c in self._room_host_cache[room]]).encode("UTF-8"),
                        )
                    )

            if not foundUniventionObjectFlag and "univentionObjectFlag" not in blacklisted_attributes:
                al.append(("univentionObjectFlag", [b"temporary"]))

            if exam_user_description and "description" not in blacklisted_attributes:
                al.append(("description", [exam_user_description.encode("UTF-8")]))

            # call hook scripts
            al = self.run_pre_create_hooks(exam_user_dn, al, ldap_admin_write)

            # And create the exam_user
            ldap_admin_write.add(exam_user_dn, al)

            # test if it worked
            try:
                exam_student = ExamStudent.from_dn(exam_user_dn, None, ldap_admin_write)
            except univention.admin.uexceptions.noObject as exc:
                raise UMC_Error(
                    _("ExamStudent %(exam_user_dn)r added to LDAP but cannot be loaded: %(exc)r.")
                    % {"exam_user_dn": exam_user_dn, "exc": exc}
                )
            except univention.admin.uexceptions.ldapError:
                raise
            logger.info("ExamStudent created sucessfully: %r", exam_student)

        except BaseException as exc:
            for i, j in alloc:
                univention.admin.allocators.release(ldap_admin_write, ldap_position, i, j)
            logger.exception("Creation of exam user account failed: %s", exc)
            raise

        # finally confirm allocated IDs
        univention.admin.allocators.confirm(ldap_admin_write, ldap_position, "uid", exam_user_uid)
        univention.admin.allocators.confirm(ldap_admin_write, ldap_position, "sid", userSid)
        univention.admin.allocators.confirm(ldap_admin_write, ldap_position, "uidNumber", uidNum)

        self.finished(request.id, {"success": True, "userdn": userdn, "examuserdn": exam_user_dn})

    @sanitize(
        users=ListSanitizer(DNSanitizer(required=True), required=True),
        school=StringSanitizer(required=True),
    )
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def add_exam_users_to_groups(
        self, request, ldap_user_read=None, ldap_admin_write=None, ldap_position=None
    ):
        """Add previously created exam users to groups."""
        self._room_host_cache.clear()
        logger.info("school=%r users=%r", request.options["school"], request.options["users"])

        groups = defaultdict(dict)
        exam_group = self.examGroup(ldap_admin_write, ldap_position, request.options["school"])

        for user_dn in request.options["users"]:
            logger.info("Adding exam student %r to exam group %r...", user_dn, exam_group["name"])
            try:
                ori_student = Student.from_dn(user_dn, None, ldap_admin_write)
            except univention.admin.uexceptions.noObject as exc:
                raise UMC_Error(
                    _("Student %(user_dn)r not found: %(exc)r.") % {"user_dn": user_dn, "exc": exc}
                )
            exam_user_uid = "".join((self._examUserPrefix, ori_student.name))
            exam_student = ExamStudent.get_only_udm_obj(
                ldap_admin_write, filter_format("uid=%s", (exam_user_uid,))
            )
            if exam_student is None:
                raise UMC_Error(
                    _("Exam user %(exam_user_uid)r not found.") % {"exam_user_uid": exam_user_uid}
                )

            udm_ori_student = ori_student.get_udm_object(ldap_admin_write)
            groups[udm_ori_student["primaryGroup"]].setdefault("dns", set()).add(exam_student.dn)
            groups[udm_ori_student["primaryGroup"]].setdefault("uids", set()).add(
                exam_student["username"]
            )
            for grp in udm_ori_student.info.get("groups", []):
                groups[grp].setdefault("dns", set()).add(exam_student.dn)
                groups[grp].setdefault("uids", set()).add(exam_student["username"])

            groups[exam_group.dn].setdefault("dns", set()).add(exam_student.dn)
            groups[exam_group.dn].setdefault("uids", set()).add(exam_student["username"])

            if "groups/group" not in self._udm_modules:
                self._udm_modules["groups/group"] = univention.admin.modules.get("groups/group")
                univention.admin.modules.init(
                    ldap_admin_write, ldap_position, self._udm_modules["groups/group"]
                )
            module_groups_group = self._udm_modules["groups/group"]

        for group_dn, users in groups.items():
            if self._examGroupExcludeRegEx and self._examGroupExcludeRegEx.search(group_dn):
                logger.info("ignoring group %r as requested via regexp", group_dn)
                continue
            grpobj = module_groups_group.object(None, ldap_admin_write, ldap_position, group_dn)
            logger.info("Adding users %r to group %r...", users["uids"], group_dn)
            grpobj.fast_member_add(users["dns"], users["uids"])

        self.finished(request.id, None)

    @sanitize(
        userdns=ListSanitizer(DNSanitizer(required=True), required=True),
        exam=StringSanitizer(default=""),
    )
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def remove_users_from_non_primary_groups(
        self, request, ldap_user_read=None, ldap_admin_write=None, ldap_position=None
    ):
        """
        This method removes the specified users (<userdns>) from their non-primary groups.
        The changes are aggregated to make as few group modifications as possible, which is
        done to improve performance when dealing with groups with lots of group members.
        """
        userdns = request.options["userdns"]  # type: List[str]
        exam = request.options["exam"]  # type: str
        logger.info("Removing users from non-primary groups: userdns=%r exam=%r", userdns, exam)

        remove_list = {}  # type: Dict[str, Tuple[List[str], List[str]]]
        logger.info("Collecting non-primary groups of %d users...", len(userdns))
        for user_dn in userdns:
            logger.debug("Collecting for user %s" % user_dn)
            user_ldap_obj = ldap_user_read.get(user_dn, attr=["uid", "gidNumber"])

            # Bug 56766: Check that the received DN represents a user
            uid = user_ldap_obj.get("uid", None)
            if not uid:
                logger.error("DN %s appears not to be a user DN. This DN will be skipped." % user_dn)
                continue

            user_name = uid[0].decode("UTF-8")
            users_primary_gid = user_ldap_obj["gidNumber"][0]  # type: bytes
            for group_dn, group_attrs in ldap_user_read.search(
                filter_format("uniqueMember=%s", (user_dn,)), attr=["dn", "gidNumber"]
            ):
                if group_attrs["gidNumber"][0] != users_primary_gid:
                    try:
                        remove_list[group_dn][0].append(user_dn)
                        remove_list[group_dn][1].append(user_name)
                    except KeyError:
                        remove_list[group_dn] = ([user_dn], [user_name])
        try:
            module_groups = self._udm_modules["groups/group"]
        except KeyError:
            module_groups = univention.admin.modules.get("groups/group")
            univention.admin.modules.init(ldap_admin_write, ldap_position, module_groups)
            self._udm_modules["groups/group"] = module_groups

        for group_dn, (user_dns, user_names) in iteritems(remove_list):
            logger.info("Removing %d users from group %r...", len(user_dns), group_dn)
            grp_obj = module_groups.object(None, ldap_admin_write, ldap_position, group_dn)
            grp_obj.fast_member_remove(user_dns, user_names)

        logger.info("Finished removal from non-primary groups.")
        self.finished(request.id, None)

    @sanitize(
        userdn=StringSanitizer(required=True),
        school=StringSanitizer(default=""),
        exam=StringSanitizer(default=""),
    )
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def remove_exam_user(self, request, ldap_user_read=None, ldap_admin_write=None):
        """
        Remove an exam account cloned from a given user account.
        Also the original sambaUserWorkstations of the original user are restored.
        The exam account is removed from the special exam group.
        """
        userdn = request.options["userdn"]
        school = request.options["school"]
        exam = request.options["exam"]
        logger.info("userdn=%r school=%r exam=%r", userdn, school, exam)
        # Might be put into the lib at some point:
        # https://git.knut.univention.de/univention/ucsschool/commit/26be4bbe899d02593d946054c396c17b7abc624f  # noqa: E501
        examUserPrefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
        user_uid = str2dn(userdn)[0][0][1].replace(examUserPrefix, "", 1)
        user_module = univention.udm.UDM(ldap_admin_write, 1).get("users/user")
        search_result = list(user_module.search(filter_format("uid=%s", [user_uid])))
        if len(search_result) == 1:
            try:
                orig_udm = search_result[0]
                new_value = []
                for ws in orig_udm.props.sambaUserWorkstations:
                    new_ws = ws[1:] if ws.startswith("$") else ws
                    new_value.append(new_ws)
                orig_udm.props.sambaUserWorkstations = [ws for ws in new_value if len(ws) > 0]
                # enable original user
                if ucr.is_true("ucsschool/exam/user/disable"):
                    logger.info("Enable original user {} again.".format(orig_udm))
                    orig_udm.props.disabled = False
                orig_udm.save()
                logger.info("Original user access has been restored for %r.", orig_udm)
            except univention.admin.uexceptions.noObject:
                raise UMC_Error(_("Exam student %r not found.") % (userdn[len(examUserPrefix) :],))
        elif len(search_result) == 0:
            raise UMC_Error(_("Exam student %r not found.") % (userdn[len(examUserPrefix) :],))
        try:
            user = ExamStudent.from_dn(userdn, None, ldap_user_read)
        except univention.admin.uexceptions.noObject:
            raise UMC_Error(_("Exam student %r not found.") % (userdn,))
        except univention.admin.uexceptions.ldapError:
            raise

        if exam:
            try:
                exam_role = create_ucsschool_role_string(
                    role_exam_user, "{}-{}".format(exam, school), context_type_exam
                )
                exam_roles = [
                    role for role in user.ucsschool_roles if get_role_info(role)[1] == context_type_exam
                ]
                if len(exam_roles) < 2:
                    user.remove(ldap_admin_write)
                    logger.info("Exam user was removed: %r", user)
                else:
                    logger.warning(
                        "remove_exam_user() User %r will not be removed as he currently participates "
                        "in another exam.",
                        user.dn,
                    )
                    try:
                        user.ucsschool_roles.remove(exam_role)
                    except ValueError as exc:
                        raise UMC_Error(
                            _('Could not remove exam role "%s" from %s: %s') % exam_role, userdn, exc
                        )
                    user.modify(ldap_admin_write)
            except univention.admin.uexceptions.ldapError as exc:
                raise UMC_Error(
                    _("Could not remove exam user %(userdn)r: %(exc)s") % {"userdn": userdn, "exc": exc}
                )
        else:  # for backwards compatibility with UCS@school prior Feb'20 exam might not be set
            try:
                schools = None
                if school:
                    schools = list(set(user.schools) - {school})
                if schools:
                    logger.warning(
                        "remove_exam_user() User %r will not be removed as he currently participates "
                        "in another exam.",
                        user.dn,
                    )
                    user.schools = schools
                    user.modify(ldap_admin_write)
                else:
                    user.remove(ldap_admin_write)
            except univention.admin.uexceptions.ldapError as exc:
                raise UMC_Error(
                    _("Could not remove exam user %(userdn)r: %(exc)s") % {"userdn": userdn, "exc": exc}
                )

        self.finished(request.id, {}, success=True)

    @sanitize(roomdn=StringSanitizer(required=True), school=StringSanitizer(default=""))
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def set_computerroom_exammode(
        self, request, ldap_user_read=None, ldap_admin_write=None, ldap_position=None
    ):
        """
        Add all member hosts except teacher_computers of a given computer room to the special exam
        group.
        """
        roomdn = request.options["roomdn"]
        logger.info("roomdn=%r", roomdn)
        try:
            room = ComputerRoom.from_dn(roomdn, None, ldap_user_read)
        except univention.admin.uexceptions.noObject:
            raise UMC_Error("Room %r not found." % (roomdn,))
        except univention.admin.uexceptions.ldapError:
            raise

        teacher_pc_role = create_ucsschool_role_string(role_teacher_computer, room.school)
        exam_hosts = []
        for host in room.hosts:
            host_obj = SchoolComputer.from_dn(host, None, ldap_user_read)  # remove with Bug #49611
            host_obj = SchoolComputer.from_dn(host, None, ldap_user_read)
            if teacher_pc_role not in host_obj.ucsschool_roles:
                exam_hosts.append(host)
        # Add all host members of room to examGroup
        host_uid_list = [str2dn(uniqueMember)[0][0][1] + "$" for uniqueMember in exam_hosts]
        examGroup = self.examGroup(ldap_admin_write, ldap_position, room.school)
        # adds any uniqueMember and member listed if not already present:
        examGroup.fast_member_add(exam_hosts, host_uid_list)

        self.finished(request.id, {}, success=True)

    @sanitize(roomdn=StringSanitizer(required=True), school=StringSanitizer(default=""))
    @LDAP_Connection(USER_READ, ADMIN_WRITE)
    def unset_computerroom_exammode(
        self, request, ldap_user_read=None, ldap_admin_write=None, ldap_position=None
    ):
        """Remove all member hosts of a given computer room from the special exam group."""
        roomdn = request.options["roomdn"]
        logger.info("roomdn=%r", roomdn)
        try:
            room = ComputerRoom.from_dn(roomdn, None, ldap_user_read)
        except univention.admin.uexceptions.noObject:
            raise UMC_Error("Room %r not found." % (roomdn,))
        except univention.admin.uexceptions.ldapError:
            raise

        # Remove all host members of room from examGroup
        host_uid_list = [str2dn(uniqueMember)[0][0][1] + "$" for uniqueMember in room.hosts]
        examGroup = self.examGroup(ldap_admin_write, ldap_position, room.school)
        # removes any uniqueMember and member listed if still present:
        examGroup.fast_member_remove(room.hosts, host_uid_list)

        self.finished(request.id, {}, success=True)

    def run_pre_create_hooks(self, exam_user_dn, al, ldap_admin_write):
        if not self.exam_user_pre_create_hooks:
            add_module_logger_to_schoollib()
            pyhook_loader = ImportPyHookLoader(CREATE_USER_PRE_HOOK_DIR)
            hooks = pyhook_loader.init_hook(ExamUserPyHook, lo=ldap_admin_write, dry_run=False)
            self.exam_user_pre_create_hooks = hooks.get("pre_create", [])

        for hook in self.exam_user_pre_create_hooks:
            al = hook(exam_user_dn, al)

        return al
