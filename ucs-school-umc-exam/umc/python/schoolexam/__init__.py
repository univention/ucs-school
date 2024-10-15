#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  Starts a new exam for a specified computer room
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

import datetime
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import traceback
from itertools import chain
from typing import TYPE_CHECKING, List, Optional  # noqa: F401

import ldap
from ldap.dn import escape_dn_chars
from ldap.filter import filter_format
from samba.auth_util import system_session_unix
from samba.ntacls import getntacl, setntacl
from samba.param import LoadParm
from samba.samba3 import param

import univention.debug as ud
from ucsschool.lib import internetrules
from ucsschool.lib.models.base import WrongObjectType
from ucsschool.lib.models.group import ComputerRoom, Group
from ucsschool.lib.models.user import Student, User
from ucsschool.lib.models.utils import (
    ModuleHandler,
    NotInstalled,
    UnknownPackage,
    exec_cmd,
    get_package_version,
)
from ucsschool.lib.roles import (
    context_type_exam,
    create_ucsschool_role_string,
    get_role_info,
    role_exam_user,
)
from ucsschool.lib.school_umc_base import Display, SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from ucsschool.lib.schoolldap import SchoolSearchBase
from ucsschool.lib.schoollessons import SchoolLessons
from univention.admin.uexceptions import noObject
from univention.lib.i18n import Translation
from univention.lib.misc import custom_groupname
from univention.lib.umc import Client, ConnectionError, Forbidden, HTTPError
from univention.management.console.config import ucr
from univention.management.console.modules import UMC_Error, computerroom
from univention.management.console.modules.decorators import (
    SimpleThread,
    file_upload,
    sanitize,
    simple_response,
)
from univention.management.console.modules.distribution import compare_dn
from univention.management.console.modules.sanitizers import (
    ChoicesSanitizer,
    DictSanitizer,
    DNSanitizer,
    ListSanitizer,
    PatternSanitizer,
    StringSanitizer,
)
from univention.management.console.modules.schoolexam import util

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType  # noqa: F401

_ = Translation("ucs-school-umc-exam").translate

CREATE_USER_POST_HOOK_DIR = "/usr/share/ucs-school-exam/hooks/create_exam_user_post.d/"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if "schoolexam" not in list(logger.handlers):
    _module_handler = ModuleHandler(udebug_facility=ud.MODULE)
    _module_handler.set_name("schoolexam")
    _formatter = logging.Formatter(fmt="%(funcName)s:%(lineno)d  %(message)s")
    _module_handler.setFormatter(_formatter)
    logger.addHandler(_module_handler)


def load_smb_default_file() -> Optional[LoadParm]:
    """
    Try to load the default samba shares.conf and retry if this fails.
    Bug 57367

    :raises: UMC_Error
    """
    lp = LoadParm()
    attempts = 5
    for i in range(attempts):
        try:
            lp.load_default()
            return lp
        except RuntimeError:
            logger.warning(
                "Failed to load samba config. "
                "Please check /etc/samba/shares.conf and linked file. "
                "Retrying in a couple of seconds."
            )
            time.sleep(2)
    else:
        logger.error(f"Failed to load the samba config {attempts} times.")
        raise UMC_Error(
            _(
                "Please contact an administrator.\n"
                "An error occurred while loading one of the samba share configuration files "
                "(see configuration file /etc/samba/shares.conf and configuration files"
                " below /etc/samba/shares.conf.d/). "
                "Known causes for this are wrong file permissions and typos in the configuration files."
            )
        )


class Instance(SchoolBaseModule):
    def __init__(self):
        SchoolBaseModule.__init__(self)
        self._log_package_version("ucs-school-umc-exam")
        self._tmpDir = None
        self._progress_state = util.Progress(logger=logger)  # TODO: replace with mixins.Progress
        self._lessons = SchoolLessons()
        self.lp = None

    def init(self):
        SchoolBaseModule.init(self)
        # initiate paths for data distribution
        util.distribution.initPaths()
        self.lp = load_smb_default_file()

    def destroy(self):
        # clean temporary data
        self._cleanTmpDir()

    @staticmethod
    def _log_package_version(package_name):  # type: (str) -> None
        try:
            logger.info(
                "Package %r installed in version %r.", package_name, get_package_version(package_name)
            )
        except (NotInstalled, UnknownPackage) as exc:
            logger.error("Error retrieving package verion: %s", exc)

    def _cleanTmpDir(self):
        # copied from distribution module
        # clean up the temporary upload directory
        if self._tmpDir:
            logger.info("Clean up temporary directory: %s", self._tmpDir)
            shutil.rmtree(self._tmpDir, ignore_errors=True)
            self._tmpDir = None

    def _get_computerroom_module(self, request):
        room_module = computerroom.Instance()
        room_module.prepare(request)
        return room_module

    @staticmethod
    @LDAP_Connection()
    def init_windows_profiles(exam_user, ldap_user_read=None):  # type: (User, LoType) -> None
        """
        When login with smbclient, the folder windows-profile and others
        are created. We need those folders to be present at this time to set the
        permissions for them, too.

        :param exam_user:
        :param ldap_user_read:
        """
        ldap_user = ldap_user_read.get(exam_user.dn)
        workstation = ldap_user.get("sambaUserWorkstations", [b""])[0].decode("UTF-8")
        password = ldap_user.get("sambaNTPassword", [b""])[0].decode("ASCII")

        if not password:
            logger.warning(
                f"User {exam_user.dn} is missing a password."
                "They will be allowed to modify the permissions of their distribution folder,"
                "which can be exploited to share data during the exam."
            )
            return
        with tempfile.NamedTemporaryFile("w+") as auth_file:
            auth_file.write(
                f"""username={exam_user.username}
                   password={password}
                   domain={ucr['domainname']}"""
            )
            auth_file.flush()

            cmd = [
                "smbclient",
                "--pw-nt-hash",
                "--authentication-file={}".format(auth_file.name),
                "-L",
                "localhost",
            ]
            if workstation:
                workstation = workstation.split(",")[0]
                cmd.append(f"--netbiosname={workstation}")
            else:
                logger.debug(
                    f"{exam_user.dn} is missing a workstation. The exam-user will be able to login to "
                    "workstations outside the computerroom."
                )
            rv, stdout, stderr = exec_cmd(cmd)
            if rv != 0:
                logger.error(
                    f"Error while initiating windows-profiles for {exam_user.dn} rv: {rv} {stderr!r}"
                    f" {stdout!r}"
                )

    def deny_owner_change_permissions(self, filename: str) -> None:
        """
        A user gets full control over her permissions by default.
        The SDDL string of the home dir is extended by
        - forbid exam-users to change the permissions and owner
        - overrides standard behavior, i.e. full control, with 'edit' for owners.
        """
        s3conf = param.get_context()
        s3conf.load(self.lp.configfile)
        dacl = getntacl(self.lp, filename, system_session_unix(), direct_db_access=False)
        old_sddl = dacl.as_sddl()
        owner_sid = dacl.owner_sid
        res = re.search(r"(O:.+?G:.+?)D:[^\(]*(.+)", old_sddl)
        if res:
            owner = res.group(1)
            old_aces = res.group(2)
            old_aces = re.findall(r"\(.+?\)", old_aces)
            allow_aces = "".join([ace for ace in old_aces if "A;" in ace])
            deny_aces = "".join([ace for ace in old_aces if "D;" in ace])
            # deny user change of permissions and owner
            new_deny_aces = "(D;OICI;WOWD;;;{})".format(owner_sid)
            new_allow_ace = [
                "(A;OICI;0x001301BF;;;S-1-3-4)",  # change default behaviour for owners to modify
                "(A;OICI;0x001301BF;;;{})".format(owner_sid),  # add modify ace for owner
            ]
            if new_deny_aces not in deny_aces:
                deny_aces += new_deny_aces
            for ace in new_allow_ace:
                if ace not in allow_aces:
                    allow_aces += ace
            new_sddl = "{}D:PAI{}{}".format(owner, deny_aces.strip(), allow_aces.strip())
            if new_sddl != old_sddl:
                logger.debug("set nt acls {} on {}".format(new_sddl, filename))
                setntacl(self.lp, filename, new_sddl, owner_sid, system_session_unix())

    def set_nt_acls_on_exam_folders(self, exam_users: List[User]) -> None:
        """
        Sets NT ACLs for exam users home dirs

        :param exam_users:
        """
        logger.info("users=%r", [u.username for u in exam_users])
        for exam_user in exam_users:
            folder = exam_user.unixhome
            Instance.init_windows_profiles(exam_user)
            for root, _sub, files in os.walk(folder):
                self.deny_owner_change_permissions(filename=root)
                for f in files:
                    self.deny_owner_change_permissions(filename=str(os.path.join(root, f)))

    @staticmethod
    def set_datadir_immutable_flag(users, project, flag=True):
        """
        Sets or unsets the immutable bit on the recipients datadir depending on the flag
        :param project: The project to calculate the project directory
        :param users: The users to (un)set the immutable bit for
        :param flag: True to set the flag, False to unset
        """
        logger.info("users=%r project=%r flag=%r", [u.username for u in users], project.name, flag)
        modifier = "+i" if flag else "-i"
        for user in users:
            # make datadir immutable
            datadir = os.path.dirname(project.user_projectdir(user).rstrip("/"))
            if os.path.exists(datadir):
                try:
                    subprocess.check_call(["/usr/bin/chattr", modifier, datadir])  # nosec
                except subprocess.CalledProcessError:
                    logger.error("Could not set the immutable bit on %r", datadir)

    @file_upload
    @sanitize(
        DictSanitizer(
            {"filename": StringSanitizer(required=True), "tmpfile": StringSanitizer(required=True)},
            required=True,
        )
    )
    def upload(self, request):
        # copied from distribution module
        # create a temporary upload directory, if it does not already exist
        logger.info("request.options=%r", request.options)
        if not self._tmpDir:
            self._tmpDir = tempfile.mkdtemp(prefix="ucsschool-exam-upload-")
            logger.info("upload() Created temporary directory: %r", self._tmpDir)

        for file in request.options:
            filename = file["filename"]
            if "\\" in filename:  # filename seems to be a UNC / windows path
                filename = filename.rsplit("\\", 1)[-1] or filename.replace("\\", "_").lstrip("_")
                logger.info(
                    "Filename seems to contain Windows path name or UNC - " "fixing filename: %r as %r",
                    file["filename"],
                    filename,
                )
            destPath = os.path.join(self._tmpDir, filename)
            logger.info("upload() Received file %r, saving it to %r", file["tmpfile"], destPath)
            shutil.move(file["tmpfile"], destPath)

        self.finished(request.id, None)

    @simple_response
    def internetrules(self):
        # copied from computerroom module
        """Returns a list of available internet rules"""
        return [x.name for x in internetrules.list()]

    @simple_response
    def lesson_end(self):
        current = self._lessons.current
        if current is not None:
            return current.end.strftime("%H:%M")
        return (datetime.datetime.now() + datetime.timedelta(minutes=45)).strftime("%H:%M")

    @simple_response
    def progress(self):
        return self._progress_state.poll()

    @LDAP_Connection()
    def _user_can_modify(self, user, exam, ldap_user_read=None):
        """
        Checks whether the given user is allowed to modify the given exam or not.
        Domain Admin: Can always modify
        School Admin: Can modify if exam owner is in own school
        Else: if owner is caller
        :param user: The user school object
        :param exam: The exam to be modified
        :return: True if user can modify else False
        """
        logger.info("user=%r exam=%r", user, exam)
        if user.dn == exam.sender.dn:
            return True
        sender_user = User.from_dn(exam.sender.dn, None, ldap_user_read)
        if (
            user.is_administrator(ldap_user_read)
            and len(set(sender_user.schools).intersection(user.schools)) != 0
        ):
            return True
        admin_group_dn = "cn=%s,cn=groups,%s" % (
            escape_dn_chars(custom_groupname("Domain Admins", ucr)),
            ucr["ldap/base"],
        )
        return admin_group_dn in user.get_udm_object(ldap_user_read)["groups"]

    @LDAP_Connection()
    def _save_exam(self, request, update=False, ldap_user_read=None):
        """
        Creates or updates an exam with the information given in the request object
        :param request: The request containing all information about the exam
        :param update: If True it is expected that an exam with the same name already exists and will
            be updated
        :return: univention.management.console.modules.distribution.util.Project
        :raises: UMC_Error
        """
        logger.info("request.options=%r update=%r", request.options, update)
        # create a User object for the teacher
        sender = util.distribution.openRecipients(request.user_dn, ldap_user_read)
        recipients = [
            util.distribution.openRecipients(i_dn, ldap_user_read)
            for i_dn in request.options.get("recipients", [])
        ]
        recipients = [recipient for recipient in recipients if recipient]
        new_values = {
            "name": request.options["directory"],
            "description": request.options["name"],
            "files": request.options.get("files"),
            "sender": sender,
            "room": request.options["room"],
            "recipients": recipients,
            "deadline": request.options["examEndTime"],
        }
        if not sender:
            raise UMC_Error(_('Could not authenticate user "%s"!') % request.user_dn)
        project = util.distribution.Project.load(request.options.get("name", ""))
        logger.info("loaded project=%r", project)
        orig_files = []
        if update:
            if not project:
                raise UMC_Error(
                    _("The specified exam does not exist: %s") % request.options.get("name", "")
                )
            # make sure that the project owner himself is modifying the project
            if not compare_dn(project.sender.dn, request.user_dn):
                raise UMC_Error(_("The exam can only be modified by the owner himself."))
            if project.isDistributed:
                raise UMC_Error(_("The exam was already started and can not be modified anymore!"))
            orig_files = project.files
            logger.info("updating project=%r with new_values=%r", project, new_values)
            project.update(new_values)
        else:
            if project:
                raise UMC_Error(
                    _(
                        'An exam with the name "%s" already exists. Please choose a different name '
                        "for the exam."
                    )
                    % new_values["name"]
                )
            project = util.distribution.Project(new_values)
            logger.info("project=%r", project)

        try:
            project.validate()
        except ValueError as exc:
            raise UMC_Error(str(exc))

        project.save()
        # copy files into project directory
        if self._tmpDir:
            for i_file in project.files:
                i_src = os.path.join(self._tmpDir, i_file)
                i_target = os.path.join(project.cachedir, i_file)
                if os.path.exists(i_src):
                    # copy file to cachedir
                    shutil.move(i_src, i_target)
                    os.chown(i_target, 0, 0)
        if update:
            for i_file in set(orig_files) - set(project.files):
                i_target = os.path.join(project.cachedir, i_file)
                try:
                    os.remove(i_target)
                except OSError:
                    pass
        return project

    @LDAP_Connection()
    def _delete_exam(self, name, ldap_user_read=None):
        """
        Deletes an exam project file including the uploaded data if the exam was not started yet and
        the caller is authorized to do so.

        :param name: Name of the exam to delete
        :return: True if exam was deleted, else False
        """
        logger.info("name=%r", name)
        exam = util.distribution.Project.load(name)
        logger.info("loaded exam=%r", exam.dict)
        if not exam:
            return False
        if exam.isDistributed:
            return False
        if not self._user_can_modify(User.from_dn(ldap_user_read.whoami(), None, ldap_user_read), exam):
            return False
        logger.info("purge exam=%r", exam.dict)
        exam.purge()
        return True

    @sanitize(StringSanitizer(required=True))
    def get(self, request):
        logger.info("request.options=%r", request.options)
        result = []
        for project in [util.distribution.Project.load(iid) for iid in request.options]:
            if not project:
                continue
            logger.info("loaded project=%r", project)  # .dict)
            # make sure that only the project owner himself (or an admin) is able
            # to see the content of a project
            if not compare_dn(project.sender.dn, request.user_dn):
                raise UMC_Error(
                    _("Exam details are only visible to the exam owner himself."), status=403
                )
            props = project.dict
            props["sender"] = props["sender"].username
            recipients = []
            for recip in props["recipients"]:
                recipients.append(
                    {
                        "id": recip.dn,
                        "label": recip.type == util.distribution.TYPE_USER
                        and Display.user(recip.dict)
                        or recip.name,
                    }
                )
            props["recipients"] = recipients
            props["examEndTime"] = props["deadline"]
            result.append(props)
        self.finished(request.id, result)

    @sanitize(
        name=StringSanitizer(required=True),
        room=StringSanitizer(required=True),
        school=SchoolSanitizer(required=True),
        directory=StringSanitizer(required=True),
        shareMode=StringSanitizer(required=True),
        internetRule=StringSanitizer(required=True),
        customRule=StringSanitizer(),
        examEndTime=StringSanitizer(required=True),
        recipients=ListSanitizer(StringSanitizer(minimum=1), required=True),
        files=ListSanitizer(StringSanitizer()),
    )
    def add(self, request):
        self._save_exam(request)
        self.finished(request.id, True)

    @sanitize(exams=ListSanitizer(StringSanitizer(minimum=1), required=True))
    def delete(self, request):
        result = []
        for exam in request.options["exams"]:
            result.append(self._delete_exam(exam))
        self.finished(request.id, result)

    @sanitize(
        name=StringSanitizer(required=True),
        room=StringSanitizer(required=True),
        school=SchoolSanitizer(required=True),
        directory=StringSanitizer(required=True),
        shareMode=StringSanitizer(required=True),
        internetRule=StringSanitizer(required=True),
        customRule=StringSanitizer(),
        examEndTime=StringSanitizer(required=True),
        recipients=ListSanitizer(StringSanitizer(minimum=1), required=True),
        files=ListSanitizer(StringSanitizer()),
    )
    def put(self, request):
        self._save_exam(request, update=True)
        self.finished(request.id, True)

    @sanitize(
        name=StringSanitizer(required=True),
        room=StringSanitizer(required=True),
        school=SchoolSanitizer(required=True),
        directory=StringSanitizer(required=True),
        shareMode=StringSanitizer(required=True),
        internetRule=StringSanitizer(required=True),
        customRule=StringSanitizer(),
        examEndTime=StringSanitizer(required=True),
        recipients=ListSanitizer(StringSanitizer(minimum=1), required=True),
        files=ListSanitizer(StringSanitizer()),
    )
    @LDAP_Connection()
    def start_exam(self, request, ldap_user_read=None, ldap_position=None):
        logger.info("request.options=%r", request.options)
        # reset the current progress state
        # steps:
        #   5  -> for preparing exam room
        #   25 -> for cloning users
        #   25 -> for each replicated users + copy of the profile directory
        #   20 -> distribution of exam files
        #   10  -> setting room properties
        progress = self._progress_state
        progress.reset(85)
        progress.component(_("Initializing"))

        # create that holds a reference to project, otherwise _thread() cannot
        # set the project variable in the scope of start_exam:
        my = type("", (), {"project": None})()

        # create a User object for the teacher
        # perform this LDAP operation outside the thread, to avoid tracebacks
        # in case of an LDAP timeout
        sender = util.distribution.openRecipients(request.user_dn, ldap_user_read)
        if not sender:
            raise UMC_Error(_('Could not authenticate user "%s"!') % request.user_dn)

        def _thread():
            project = util.distribution.Project.load(request.options.get("name", ""))
            logger.info("loaded project=%r", project)
            directory = request.options["directory"]
            if project:
                my.project = self._save_exam(request, update=True, ldap_user_read=ldap_user_read)
            else:
                my.project = self._save_exam(request, update=False, ldap_user_read=ldap_user_read)
            logger.info("after saving exam: my.project=%r", my.project)

            # open a new connection to the Primary Directory Node UMC
            try:
                master = ucr["ldap/master"]
                client = Client(master)
                client.authenticate_with_machine_account()
            except (ConnectionError, HTTPError) as exc:
                logger.error("start_exam() Could not connect to UMC on %s: %s", master, exc)
                raise UMC_Error(
                    _("Could not connect to Primary Directory Node %s.") % ucr.get("ldap/master")
                )

            # mark the computer room for exam mode
            progress.component(_("Preparing the computer room for exam mode..."))
            client.umc_command(  # noqa: B018
                "schoolexam-master/set-computerroom-exammode",
                {"school": request.options["school"], "roomdn": request.options["room"]},
            ).result  # FIXME: no error handling
            progress.add_steps(5)

            # read all recipients and fetch all user objects
            users = []
            for idn in request.options["recipients"]:
                ientry = util.distribution.openRecipients(idn, ldap_user_read)
                if not ientry:
                    continue
                # recipients can in theory be users or groups
                members = []
                if isinstance(ientry, util.distribution.User):
                    members = [ientry]
                elif isinstance(ientry, util.distribution.Group):
                    members = ientry.members
                for entry in members:
                    # ignore all users except students
                    user = User.from_dn(entry.dn, None, ldap_user_read)
                    if user.is_student(ldap_user_read) and not user.is_exam_student(ldap_user_read):
                        users.append(entry)

            # start to create exam user accounts
            progress.component(_("Preparing exam accounts"))
            percentPerUser = 25.0 / (1 + len(users))
            examUsers = set()
            student_dns = set()
            usersReplicated = set()
            for num, iuser in enumerate(users, start=1):
                logger.info(
                    "start_exam() Requesting exam user %02d/%02d to be created: %r",
                    num,
                    len(users),
                    iuser.dn,
                )
                progress.info(
                    "(%02d/%02d) %s, %s (%s)"
                    % (num, len(users), iuser.lastname, iuser.firstname, iuser.username)
                )
                try:
                    ires = client.umc_command(
                        "schoolexam-master/create-exam-user",
                        {
                            "school": request.options["school"],
                            "userdn": iuser.dn,
                            "room": request.options["room"],
                            "exam": request.options["name"],
                        },
                    ).result
                    if not ires:  # occurs if disabled user gets ignored
                        continue
                    examuser_dn = ires.get("examuserdn")
                    examUsers.add(examuser_dn)
                    student_dns.add(iuser.dn)
                    logger.info("start_exam() Exam user has been created: %r", examuser_dn)
                except (ConnectionError, HTTPError) as exc:
                    logger.warning(
                        "start_exam() Could not create exam user account for %r: %s", iuser.dn, exc
                    )

                # indicate the the user has been processed
                progress.add_steps(percentPerUser)

            logger.info(
                "start_exam() Sending DNs to add to group to Primary Directory Node: %r", student_dns
            )
            client.umc_command(
                "schoolexam-master/add-exam-users-to-groups",
                {"users": list(student_dns), "school": request.options["school"]},
            )

            progress.add_steps(percentPerUser)
            # wait for the replication of all users to be finished
            progress.component(_("Preparing user home directories"))
            recipients = []  # list of User objects for all exam users
            openAttempts = 30 * 60  # wait max. 30 minutes for replication
            while (len(examUsers) > len(usersReplicated)) and (openAttempts > 0):
                openAttempts -= 1
                logger.info(
                    "start_exam() waiting for replication to be finished, %d user objects missing",
                    len(examUsers) - len(usersReplicated),
                )
                for idn in examUsers - usersReplicated:
                    try:
                        ldap_user_read.get(idn, required=True)
                    except ldap.NO_SUCH_OBJECT:
                        continue  # not replicated yet
                    iuser = util.distribution.openRecipients(idn, ldap_user_read)
                    if not iuser:
                        continue  # not a users/user object
                    logger.info("user has been replicated: %r", idn)

                    # Bug #52307:
                    # Creating two exams quickly in succession leads to the
                    # second exam mode using the same UIDs as the first.
                    # -> clear user name cache to force Samba to get the
                    # new UID from ldap.
                    logger.info("Clear user name cache...")
                    cmd = ["/usr/sbin/nscd", "-i", "passwd"]
                    if subprocess.call(cmd):  # nosec
                        logger.error("Clearing user name cache failed: %s", " ".join(cmd))
                    else:
                        logger.info("Clearing user name cache finished successfully.")

                    # call hook scripts
                    if 0 != subprocess.call(  # nosec
                        [
                            "/bin/run-parts",
                            CREATE_USER_POST_HOOK_DIR,
                            "--arg",
                            iuser.username,
                            "--arg",
                            iuser.dn,
                            "--arg",
                            iuser.homedir,
                        ]
                    ):
                        raise ValueError(f"failed to run hook scripts for user {iuser.username!r}")

                    # store User object in list of final recipients
                    recipients.append(iuser)

                    # mark the user as replicated
                    usersReplicated.add(idn)
                    progress.info(
                        f"({len(usersReplicated):02d}/{len(examUsers):02d}) {iuser.lastname}, "
                        f"{iuser.firstname} ({iuser.username})"
                    )
                    progress.add_steps(percentPerUser)

                # wait a second
                time.sleep(1)

            progress.add_steps(percentPerUser)

            if openAttempts <= 0:
                logger.error(
                    "replication timeout - %d user objects missing: %r ",
                    (len(examUsers) - len(usersReplicated)),
                    (examUsers - usersReplicated),
                )
                raise UMC_Error(_("Replication timeout: could not create all exam users"))

            # update the final list of recipients
            my.project.recipients = recipients
            my.project.save()

            # update local NSS group cache
            progress.info("Updating local nss group cache...")
            if ucr.is_true("nss/group/cachefile", True):
                cmd = ["/usr/lib/univention-pam/ldap-group-to-file.py"]
                if ucr.is_true("nss/group/cachefile/check_member", False):
                    cmd.append("--check_member")
                logger.info("Updating local nss group cache...")
                if subprocess.call(cmd):  # nosec
                    logger.error("Updating local nss group cache failed: %s", " ".join(cmd))
                else:
                    logger.info("Update of local nss group cache finished successfully.")

            # distribute exam files
            progress.component(_("Distributing exam files"))
            progress.info("")
            Instance.set_datadir_immutable_flag(my.project.getRecipients(), my.project, False)
            my.project.distribute()
            Instance.set_datadir_immutable_flag(my.project.getRecipients(), my.project, True)
            progress.add_steps(20)

            # prepare room settings via lib...
            #   first step: acquire room
            #   second step: adjust room settings
            progress.component(_("Prepare room settings"))

            room = request.options["room"]
            logger.info("Acquire room: %s", room)
            room_module = self._get_computerroom_module(request)
            room_module._room_acquire(request, request.options["room"], ldap_user_read)
            progress.add_steps(1)
            logger.info(
                "Adjust room settings:\n%s",
                "\n".join(f"  {k}={v}" for k, v in request.options.items()),
            )
            room_module._start_exam(
                request, room, directory, request.options["name"], request.options.get("examEndTime")
            )
            progress.add_steps(4)
            room_module._settings_set(
                request,
                "default",
                request.options["internetRule"],
                request.options["shareMode"],
                customRule=request.options.get("customRule"),
            )
            # wait for samba-replication
            progress.add_steps(5)
            Instance.set_datadir_immutable_flag(my.project.getRecipients(), my.project, False)
            self.set_nt_acls_on_exam_folders(my.project.getRecipients())
            Instance.set_datadir_immutable_flag(my.project.getRecipients(), my.project, True)
            progress.add_steps(5)

        def _finished(thread, result, request):
            logger.info("result=%r", result)

            # mark the progress state as finished
            progress.info(_("finished..."))
            progress.finish()

            # finish the request at the end in order to force the module to keep
            # running until all actions have been completed
            success = not isinstance(result, BaseException)

            try:
                if my.project:
                    my.project.starttime = datetime.datetime.now()
                    my.project.save()
            except Exception:
                logger.exception("Could not save new project starttime.")

            if success:
                response = {"success": True}
                # remove uploaded files from cache
                self._cleanTmpDir()
            else:
                msg = str(result)
                response = result
                if not isinstance(result, UMC_Error):
                    msg = "".join(traceback.format_exception(*thread.exc_info))  # FIXME
                progress.error(msg)

                try:
                    # in case a distribution project has already be written to disk, purge it
                    if my.project:
                        logger.info("purge my.project=%r", my.project)
                        my.project.purge()
                except Exception:
                    logger.exception("Could not purge project.")

            self.thread_finished_callback(thread, response, request)

        thread = SimpleThread("start_exam", _thread, lambda t, r: _finished(t, r, request))
        thread.run()

    @sanitize(exam=StringSanitizer(required=True))
    @simple_response
    def collect_exam(self, exam):
        logger.info("exam=%r", exam)
        project = util.distribution.Project.load(exam)
        if not project:
            raise UMC_Error(_("No files have been distributed"))
        logger.info("loaded project=%r", project)

        project.collect()
        return True

    @sanitize(room=DNSanitizer(required=True))
    @LDAP_Connection()
    def validate_room(self, request, ldap_user_read=None, ldap_position=None):
        error = None
        dn = request.options["room"]
        room = ComputerRoom.from_dn(dn, None, ldap_user_read)
        if not room.hosts:
            # FIXME: raise UMC_Error()
            error = (
                _(
                    'Room "%s" does not contain any computers. Empty rooms may not be used to start an '
                    "exam."
                )
                % room.get_relative_name()
            )
        self.finished(request.id, error)

    @sanitize(room=StringSanitizer(required=True), exam=StringSanitizer(required=True))
    @LDAP_Connection()
    def finish_exam(self, request, ldap_user_read=None):
        logger.info("request.options=%r", request.options)
        # reset the current progress state
        # steps:
        #   10 -> collecting exam files
        #   5 -> for preparing exam room
        #   25 -> for cloning users
        progress = self._progress_state
        progress.reset(40)
        progress.component(_("Initializing"))

        # try to open project file
        project = util.distribution.Project.load(request.options.get("exam"))
        logger.info("loaded project=%r", project)
        if not project:
            # the project file does not exist... ignore problem
            logger.warning(
                "The project file for exam %s does not exist. Ignoring and finishing exam mode.",
                request.options.get("exam"),
            )

        def _thread():
            # perform all actions inside a thread...
            # collect files
            progress.component(_("Collecting exam files..."))
            if project:
                project.collect()
                # remove immutable bit from folders
            progress.add_steps(10)

            # open a new connection to the Primary Directory Node UMC
            master = ucr["ldap/master"]
            try:
                client = Client(master)
                client.authenticate_with_machine_account()
            except (ConnectionError, HTTPError) as exc:
                logger.error("Could not connect to UMC on %s: %s", master, exc)
                raise UMC_Error(_("Could not connect to Primary Directory Node %s.") % (master,))

            school = SchoolSearchBase.getOU(request.options["room"])

            # unset exam mode for the given computer room
            progress.component(_("Configuring the computer room..."))
            client.umc_command(  # noqa: B018
                "schoolexam-master/unset-computerroom-exammode",
                {"roomdn": request.options["room"], "school": school},
            ).result
            progress.add_steps(5)

            # delete exam users accounts
            if project:
                # get a list of user accounts in parallel exams
                exam_role_str = create_ucsschool_role_string(
                    role_exam_user, f"{project.name}-{school}", context_type_exam
                )
                recipients = ldap_user_read.search(
                    filter_format(
                        "(&(ucsschoolRole=%s)(univentionObjectType=users/user))", (exam_role_str,)
                    ),
                    attr=["ucsschoolRole", "uid"],
                )
                # This is needed for backwards compatibility with any Primary Directory Node
                # that is not updated to use roles for exam membership yet.
                exam_roles_exist = any(
                    True
                    for user in recipients
                    if len(
                        [
                            role
                            for role in user[1]["ucsschoolRole"]
                            if get_role_info(role.decode("UTF-8"))[1] == context_type_exam
                        ]
                    )
                    > 0
                )
                if exam_roles_exist and len(recipients) != len(project.recipients):
                    logger.warning(
                        "Found %d recipients through exam role, but %d through the project.",
                        len(recipients),
                        len(project.recipients),
                    )

                parallel_users_local = {
                    iuser.dn: iproject.description
                    for iproject in util.distribution.Project.list(only_distributed=True)
                    if iproject.name != project.name
                    for iuser in iproject.recipients
                }
                logger.info("parallel_users_local=%r", parallel_users_local)

                progress.component(_("Removing exam accounts"))
                percentPerUser = 25.0 / (1 + len(project.recipients))

                # Bug #51199:
                # The following block speeds up the removal of several exam users by reducing the number
                # of LDAP group changes. This is especially relevant if the exam users are included in
                # many large groups (e.g. in several schools with many students). Each group change is
                # very time consuming for large groups.
                # Therefore, the group changes are first aggregated for several exam users and executed
                # as one LDAP modification per group. Only after that the Exam users are actually
                # deleted.
                users_to_reduce = []
                for recipient_dn, recipient_attrs in recipients:
                    exam_roles = [
                        role
                        for role in recipient_attrs["ucsschoolRole"]
                        if get_role_info(role.decode("UTF-8"))[1] == context_type_exam
                    ]
                    if len(exam_roles) == 1:
                        users_to_reduce.append(recipient_dn)
                if users_to_reduce:
                    logger.info(
                        "Removing non-primary groups of %d users (of %d total).",
                        len(users_to_reduce),
                        len(recipients),
                    )
                    umc_cmd = "schoolexam-master/remove-users-from-non-primary-groups"
                    try:
                        client.umc_command(  # noqa: B018
                            umc_cmd, {"userdns": users_to_reduce, "exam": request.options["exam"]}
                        ).result
                    except Forbidden as exc:
                        # Primary Directory Node has old package. No problem, as users will still be
                        # deleted in the next step, just slower.
                        logger.warning(
                            "Forbidden (HTTP %r): Primary Directory Node doesn't know UMC command %r. "
                            "Skipping non-primary-groups-removal optimization step.",
                            exc.code,
                            umc_cmd,
                        )
                else:
                    logger.info("No users to remove non-primary groups found.")

                logger.info("Deleting %d recipients...", len(project.recipients))
                for num, iuser in enumerate(project.recipients, start=1):
                    progress.info(
                        f"({num:02d}/{len(project.recipients):02d}) {iuser.lastname}, {iuser.firstname} "
                        f"({iuser.username})"
                    )
                    try:
                        if exam_roles_exist or iuser.dn not in parallel_users_local:
                            # remove LDAP user entry
                            client.umc_command(  # noqa: B018
                                "schoolexam-master/remove-exam-user",
                                {"userdn": iuser.dn, "school": school, "exam": request.options["exam"]},
                            ).result
                        if iuser.dn not in parallel_users_local:
                            Instance.set_datadir_immutable_flag([iuser], project, False)
                            # remove first the home directory, if enabled
                            if ucr.is_true("ucsschool/exam/user/homedir/autoremove", False):
                                shutil.rmtree(iuser.unixhome, ignore_errors=True)
                            logger.info("Exam user has been removed: %r", iuser.dn)
                    except (ConnectionError, HTTPError) as e:
                        logger.warning("Could not remove exam user account %r: %s", iuser.dn, e)

                    # indicate the user has been processed
                    progress.add_steps(percentPerUser)

                logger.info("Finished removing exam accounts.")
                progress.add_steps(percentPerUser)

        def _finished(thread, result):
            # mark the progress state as finished
            logger.info("result=%r", result)
            progress.info(_("finished..."))

            # running until all actions have been completed
            if isinstance(result, BaseException):
                logger.error("Exception during exam_finish: %s", result)
                progress.error(_("An unexpected error occurred during the preparation: %s") % result)
                response = {"success": False}
            else:
                response = {"success": True}

                if project:
                    logger.info("purge project=%r", project)
                    try:
                        project.purge()
                    except Exception:
                        logger.exception("Could not purge project.")

                # remove uploaded files from cache
                self._cleanTmpDir()

            progress.finish()
            self.thread_finished_callback(thread, response, request)

        thread = SimpleThread("start_exam", _thread, _finished)
        thread.run()

    @sanitize(
        pattern=PatternSanitizer(required=False, default=".*"),
        filter=ChoicesSanitizer(["all", "private"], default="private"),
    )
    @LDAP_Connection()
    def query(self, request, ldap_user_read=None):
        """
        Get all exams (both running and planned).

        :param _sre.SRE_Pattern pattern: pattern that the result lists
            project names is matched against, defaults to `.*` (compiled by
            decorator).
        :param str filter: filter result list by project creator ("sender").
            Must be either `all` or `private`, defaults to `private`.
        :return: list of projects
        :rtype: list(dict)
        """
        pattern = request.options["pattern"]
        filter = request.options["filter"]
        user = User.from_dn(ldap_user_read.whoami(), None, ldap_user_read)
        result = [
            {
                "name": project.name,
                "sender": project.sender.username,  # teacher / admins
                "recipientsGroups": [
                    g.name for g in project.recipients if g.type == util.distribution.TYPE_GROUP
                ],
                "recipientsStudents": self._get_project_students(project, ldap_user_read),
                "starttime": project.starttime.strftime("%Y-%m-%d %H:%M") if project.starttime else "",
                "files": len(project.files) if project.files else 0,
                "isDistributed": project.isDistributed,
                "callerCanModify": self._user_can_modify(user, project),
                "room": ComputerRoom.get_name_from_dn(project.room) if project.room else "",
            }
            for project in util.distribution.Project.list()
            if pattern.match(project.name)
            and (filter == "all" or compare_dn(project.sender.dn, request.user_dn))
        ]
        self.finished(request.id, result)  # cannot use @simple_response with @LDAP_Connection :/

    def _get_project_students(self, project, lo):
        temp_students = [s for s in project.recipients if s.type == util.distribution.TYPE_USER]
        temp_students += list(
            chain.from_iterable(
                g.members for g in project.recipients if g.type == util.distribution.TYPE_GROUP
            )
        )
        project_students = []
        for student in {(s.username, s.dn) for s in temp_students}:
            try:
                user_obj = User.from_dn(student[1], None, lo)
            except noObject:
                logger.warning(
                    "DN %r is stored as part of project %r but does not exist.", student[1], project.name
                )
                continue
            if (
                not project.isDistributed
                and user_obj.is_student(lo)
                and not user_obj.is_exam_student(lo)
            ):
                project_students.append(student[0])
            elif project.isDistributed and user_obj.is_exam_student(lo):
                project_students.append(student[0])
        return project_students

    @sanitize(groups=ListSanitizer(DNSanitizer(minimum=1), required=True, min_elements=1))
    @LDAP_Connection()
    def groups2students(self, request, ldap_user_read=None):
        """
        Get members of passed groups. Only students are returned.

        request.options must contain a key `groups` with a list of DNs (only
        ucsschool.lib WorkGroup and SchoolClass are supported).

        The UMC call will return a list of dicts::

            [{'dn': …, 'firstname': …, 'lastname': …, 'school_classes': …}, …]
        """
        students = {}
        for group_dn in request.options["groups"]:
            try:
                group_obj = Group.from_dn(group_dn, None, ldap_user_read)
            except (WrongObjectType, noObject) as exc:
                logger.error(
                    "DN %r does not exist or is not a work group or school class: %s", group_dn, exc
                )
                raise UMC_Error(_("Error loading group DN {!r}.").format(group_dn))

            school_class_name = group_obj.name[len(group_obj.school) + 1 :]

            for user_dn in group_obj.users:
                try:
                    user_obj = User.from_dn(user_dn, None, ldap_user_read)
                except (WrongObjectType, noObject) as exc:
                    logger.warning(
                        "Ignoring DN %r - it does not exist or is not a school user: %s", user_dn, exc
                    )
                    continue

                if user_obj.is_student(ldap_user_read) and not user_obj.is_exam_student(ldap_user_read):
                    if user_dn in students:
                        students[user_dn]["school_classes"].append(school_class_name)
                    else:
                        students[user_dn] = {
                            "dn": user_dn,
                            "firstname": user_obj.firstname,
                            "lastname": user_obj.lastname,
                            "school_classes": [school_class_name],
                        }

        # Validate students
        # Bug #57319
        students_with_validation_errors = []
        for student_vals in students.values():
            logger.info("Validating student {}".format(student_vals["dn"]))
            student_obj = Student.from_dn(student_vals["dn"], None, ldap_user_read)
            student_obj.validate(ldap_user_read)
            if student_obj.errors:
                logger.error(
                    "Student {} has validation errors: \n{}".format(student_obj.dn, student_obj.errors)
                )
                students_with_validation_errors.append(student_obj)

        if students_with_validation_errors:
            formatted_errors = ""
            for student in students_with_validation_errors:
                formatted_errors += "{}\n".format(student.dn)
                for error_key, error_descriptions in student.errors.items():
                    for error_description in error_descriptions:
                        formatted_errors += "{}: {}\n".format(error_key, error_description)

            error_msg = "".join(
                [
                    _("The following students have validation errors:\n\n"),
                    formatted_errors,
                    _(
                        "\nThe student data must be corrected by an "
                        "Administrator before the students can be added to the exam."
                    ),
                ]
            )
            raise UMC_Error(error_msg)

        res = sorted(students.values(), key=lambda x: x["dn"])
        self.finished(request.id, res)  # cannot use @simple_response with @LDAP_Connection :/
