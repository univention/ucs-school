#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#
#
# Copyright 2012-2024 Univention GmbH
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

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

from six import reraise as raise_

import univention.admin.uexceptions as udm_exceptions
from ucsschool.lib.models.user import User
from ucsschool.lib.school_umc_base import Display, SchoolBaseModule
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import (
    file_upload,
    sanitize,
    simple_response,
)
from univention.management.console.modules.distribution import util
from univention.management.console.modules.sanitizers import (
    ChoicesSanitizer,
    DictSanitizer,
    ListSanitizer,
    PatternSanitizer,
    StringSanitizer,
)

_ = Translation("ucs-school-umc-distribution").translate


def compare_dn(a, b):
    return a and b and a.lower() == b.lower()


class Instance(SchoolBaseModule):
    def __init__(self):
        SchoolBaseModule.__init__(self)
        self._tmpDir = None

    def init(self):
        SchoolBaseModule.init(self)
        # initiate paths for data distribution
        util.initPaths()

    def destroy(self):
        self._cleanTmpDir()

    def _cleanTmpDir(self):
        # clean up the temporary upload directory
        if self._tmpDir:
            MODULE.info("Clean up temporary directory: %s" % self._tmpDir)
            shutil.rmtree(self._tmpDir, ignore_errors=True)
            self._tmpDir = None

    @file_upload
    @sanitize(
        DictSanitizer(
            {
                "filename": StringSanitizer(required=True),
                "tmpfile": StringSanitizer(required=True),
            },
            required=True,
        )
    )
    def upload(self, request):
        # create a temporary upload directory, if it does not already exist
        if not self._tmpDir:
            self._tmpDir = tempfile.mkdtemp(prefix="ucsschool-distribution-upload-")
            MODULE.info("Created temporary directory: %s" % self._tmpDir)

        for file in request.options:
            filename = file["filename"]
            if "\\" in filename:  # Bug 46709/46710: filename seems to be a UNC / windows path
                MODULE.info("Filename seems to contain Windows path name or UNC - fixing filename")
                filename = filename.rsplit("\\", 1)[-1] or filename.replace("\\", "_").lstrip("_")
            destPath = os.path.join(self._tmpDir, filename)
            MODULE.info("Received file %r, saving it to %r" % (file["tmpfile"], destPath))
            shutil.move(file["tmpfile"], destPath)

        self.finished(request.id, None)

    @sanitize(
        filenames=ListSanitizer(min_elements=1),
        # project=StringSanitizer(allow_none=True)
    )
    @simple_response
    def checkfiles(self, project, filenames):
        """
        Checks whether the given filename has already been uploaded:

        request.options: { 'filenames': [ '...', ... ], project: '...' }

        returns: {
            'filename': '...',
            'sessionDuplicate': True|False,
            'projectDuplicate': True|False,
            'distributed': True|False
        }
        """
        # load project
        if project:
            project = util.Project.load(project)

        result = []
        for ifile in filenames:
            # check whether file has already been upload in this session
            iresult = {
                "sessionDuplicate": False,
                "projectDuplicate": False,
                "distributed": False,
            }
            iresult["filename"] = ifile
            iresult["sessionDuplicate"] = self._tmpDir is not None and os.path.exists(
                os.path.join(self._tmpDir, ifile)
            )

            # check whether the file exists in the specified project and whether
            # it has already been distributed
            if project:
                iresult["projectDuplicate"] = ifile in project.files
                iresult["distributed"] = ifile in project.files and not os.path.exists(
                    os.path.join(project.cachedir, ifile)
                )
            result.append(iresult)
        return result

    @sanitize(
        pattern=PatternSanitizer(required=False, default=".*"),
        filter=ChoicesSanitizer(["all", "private"], default="private"),
    )
    @simple_response(with_request=True)
    def query(self, request, pattern, filter):
        result = [
            {
                # only show necessary information
                "description": i.description,
                "name": i.name,
                "sender": i.sender.username,
                "recipients": len(i.recipients),
                "files": len(i.files),
                "isDistributed": i.isDistributed,
            }
            for i in util.Project.list()
            if (pattern.match(i.name) or pattern.match(i.description))
            and (filter == "all" or compare_dn(i.sender.dn, request.user_dn))
        ]
        return result

    @LDAP_Connection()
    def _get_sender(self, request, ldap_user_read=None, ldap_position=None):
        """Return a User instance of the currently logged in user."""
        try:
            user = User.from_dn(request.user_dn, None, ldap_user_read)
            obj = user.get_udm_object(ldap_user_read)
            return util.User(obj.info, dn=obj.dn)
        except udm_exceptions.base as exc:
            raise UMC_Error(_("Failed to load user information: %s") % exc)

    @sanitize(DictSanitizer({"object": DictSanitizer({}, required=True)}, required=True))
    def put(self, request):
        """Modify an existing project"""
        result = [self._save(request, entry["object"], True) for entry in request.options]
        self.finished(request.id, result)

    @sanitize(DictSanitizer({"object": DictSanitizer({}, required=True)}, required=True))
    def add(self, request):
        """Add a new project"""
        result = [self._save(request, entry["object"], False) for entry in request.options]
        self.finished(request.id, result)

    @LDAP_Connection()
    def _save(self, request, iprops, doUpdate=True, ldap_user_read=None, ldap_position=None):
        # try to open the UDM user object of the current user
        sender = self._get_sender(request)

        try:
            # remove keys that may not be set from outside
            for k in ("atJobNumCollect", "atJobNumDistribute"):
                iprops.pop(k, None)

            # load the project or create a new one
            project = None
            orgProject = None
            if doUpdate:
                # try to load the given project
                orgProject = util.Project.load(iprops.get("name", ""))
                if not orgProject:
                    raise UMC_Error(_("The specified project does not exist: %s") % iprops["name"])

                # create a new project with the updated values
                project = util.Project(orgProject.dict)
                project.update(iprops)
            else:
                # create a new project
                project = util.Project(iprops)

            # make sure that the project owner himself is modifying the project
            if doUpdate and not compare_dn(project.sender.dn, request.user_dn):
                raise UMC_Error(_("The project can only be modified by the owner himself"))

            # handle time settings for distribution/collection of project files
            for jsuffix, jprop, jname in (
                ("distribute", "starttime", _("Project distribution")),
                ("collect", "deadline", _("Project collection")),
            ):
                if "%sType" % jsuffix in iprops:
                    # check the distribution/collection type: manual/automat
                    jtype = (iprops["%sType" % jsuffix]).lower()
                    if jtype == "automatic":
                        try:
                            # try to parse the given time parameters
                            strtime = "%s %s" % (
                                iprops["%sDate" % jsuffix],
                                iprops["%sTime" % jsuffix],
                            )
                            jdate = datetime.strptime(strtime, "%Y-%m-%d %H:%M")
                            setattr(project, jprop, jdate)
                        except ValueError:
                            raise UMC_Error(_("Could not set date for: %s") % jname)

                        # make sure the execution time lies sufficiently in the future
                        if getattr(project, jprop) - datetime.now() < timedelta(minutes=1):
                            raise UMC_Error(
                                _("The specified time needs to lie in the future for: %s") % jname
                            )
                    else:
                        # manual distribution/collection
                        setattr(project, jprop, None)

            if project.starttime and project.deadline:
                # make sure distributing happens before collecting
                if project.deadline - project.starttime < timedelta(minutes=3):
                    raise UMC_Error(
                        _(
                            "Distributing the data needs to happen sufficiently long enough before "
                            "collecting them"
                        )
                    )

            if "recipients" in iprops:
                # lookup the users in LDAP and save them to the project
                project.recipients = [
                    util.openRecipients(idn, ldap_user_read) for idn in iprops.get("recipients", [])
                ]
                project.recipients = [x for x in project.recipients if x]
                MODULE.info("recipients: %s" % (project.recipients,))

            if not doUpdate:
                # set the sender (i.e., owner) of the project
                project.sender = sender

            # initiate project and validate its values
            try:
                project.validate()
            except ValueError as exc:
                raise UMC_Error(str(exc))

            # make sure that there is no other project with the same directory name
            # if we add new projects
            if not doUpdate and project.isNameInUse():
                MODULE.error("The project name is already in use: %s" % (project.name))
                raise UMC_Error(
                    _(
                        'The specified project directory name "%s" is already in use by a different '
                        "project."
                    )
                    % (project.name)
                )

            # try to save project to disk
            project.save()

            # move new files into project directory
            if self._tmpDir:
                for ifile in project.files:
                    isrc = os.path.join(self._tmpDir, ifile)
                    itarget = os.path.join(project.cachedir, ifile)
                    if os.path.exists(isrc):
                        # mv file to cachedir
                        shutil.move(isrc, itarget)
                        os.chown(itarget, 0, 0)

            # remove files that have been marked for removal
            if doUpdate:
                for ifile in set(orgProject.files) - set(project.files):
                    itarget = os.path.join(project.cachedir, ifile)
                    try:
                        os.remove(itarget)
                    except OSError:
                        pass

            # re-distribute the project in case it has already been distributed
            if doUpdate and project.isDistributed:
                usersFailed = []
                project.distribute(usersFailed)

                if usersFailed:
                    # not all files could be distributed
                    MODULE.info("Failed processing the following users: %s" % usersFailed)
                    usersStr = ", ".join([Display.user(i) for i in usersFailed])
                    raise UMC_Error(
                        _("The project could not distributed to the following users: %s") % usersStr
                    )
        except (IOError, OSError, UMC_Error):  # TODO: catch only UMC_Error
            etype, exc, etraceback = sys.exc_info()
            # data not valid... create error info
            MODULE.info('data for project "%s" is not valid: %s' % (iprops.get("name"), exc))

            if not doUpdate:
                # remove eventually created project file and cache dir
                for ipath in (project.projectfile, project.cachedir):
                    if os.path.basename(ipath) not in os.listdir(util.DISTRIBUTION_DATA_PATH):
                        # no file / directory has been created yet
                        continue
                    try:
                        MODULE.info("cleaning up... removing: %s" % ipath)
                        shutil.rmtree(ipath)
                    except (IOError, OSError):
                        pass
            raise_(UMC_Error, exc, etraceback)
        self._cleanTmpDir()
        return {"success": True, "name": iprops.get("name")}

    @sanitize(StringSanitizer(required=True))
    @LDAP_Connection()
    def get(self, request, ldap_user_read=None, ldap_position=None):
        """
        Returns the objects for the given IDs

        requests.options = [ <ID>, ... ]

        return: [ { ... }, ... ]
        """
        # try to load all given projects
        result = []
        # list of all project properties (dicts) or None if project is not valid
        for iproject in [util.Project.load(iid) for iid in request.options]:
            # make sure that project could be loaded
            if not iproject:
                result.append(None)
                continue

            # make sure that only the project owner himself (or an admin) is able
            # to see the content of a project
            if request.flavor == "teacher" and not compare_dn(iproject.sender.dn, request.user_dn):
                raise UMC_Error(
                    _(
                        "Project details are only visible to the project owner himself or an "
                        "administrator."
                    ),
                    status=403,
                )

            # prepare date and time properties for distribution/collection of project files
            props = iproject.dict
            for jjob, jsuffix in (
                (iproject.atJobDistribute, "distribute"),
                (iproject.atJobCollect, "collect"),
            ):
                MODULE.info("check job: %s" % jsuffix)
                if not jjob:
                    # no job is registered -> manual job distribution/collection
                    MODULE.info("no existing job -> manual execution")
                    props["%sType" % jsuffix] = "manual"
                    continue

                # job is registered -> prepare date and time fields
                MODULE.info(
                    "job nr #%d scheduled for %s -> automatic execution" % (jjob.nr, jjob.execTime)
                )
                props["%sType" % jsuffix] = "automatic"
                props["%sDate" % jsuffix] = datetime.strftime(jjob.execTime, "%Y-%m-%d")
                props["%sTime" % jsuffix] = datetime.strftime(jjob.execTime, "%H:%M")

            # adjust sender / recipients properties
            props["sender"] = props["sender"].username
            recipients = []
            for recip in props["recipients"]:
                recipients.append(
                    {
                        "id": recip.dn,
                        "label": recip.type == util.TYPE_USER and Display.user(recip.dict) or recip.name,
                    }
                )
            props["recipients"] = recipients

            # append final dict to result list
            MODULE.info("final project dict: %s" % props)
            result.append(props)
        self.finished(request.id, result)

    @sanitize(StringSanitizer(required=True))
    def distribute(self, request):
        # update the sender information of the selected projects
        result = []
        for iid in request.options:
            MODULE.info("Distribute project: %s" % iid)
            try:
                # make sure that project could be loaded
                iproject = util.Project.load(iid)
                if not iproject:
                    raise IOError(_('Project "%s" could not be loaded') % iid)

                # make sure that only the project owner himself (or an admin) is able
                # to distribute a project
                if request.flavor == "teacher" and not compare_dn(iproject.sender.dn, request.user_dn):
                    raise ValueError(
                        _("Only the owner himself or an administrator may distribute a project.")
                    )

                # project was loaded successfully... try to distribute it
                usersFailed = []
                iproject.distribute(usersFailed)

                # raise an error in case distribution failed for some users
                if usersFailed:
                    MODULE.info("Failed processing the following users: %s" % usersFailed)
                    usersStr = ", ".join([Display.user(i) for i in usersFailed])
                    raise IOError(
                        _("The project could not distributed to the following users: %s") % usersStr
                    )

                # save result
                result.append({"name": iid, "success": True})
            except (ValueError, IOError) as exc:
                result.append({"name": iid, "success": False, "details": str(exc)})

        # return the results
        self.finished(request.id, result)

    @sanitize(StringSanitizer(required=True))
    def collect(self, request):
        # try to open the UDM user object of the current user
        sender = self._get_sender(request)

        # update the sender information of the selected projects
        result = []
        for iid in request.options:
            MODULE.info("Collect project: %s" % iid)
            try:
                # make sure that project could be loaded
                iproject = util.Project.load(iid)
                if not iproject:
                    raise IOError(_('Project "%s" could not be loaded') % iid)

                # replace the projects sender with the current logged in user
                iproject.sender = sender

                # project was loaded successfully... try to distribute it
                dirsFailed = []
                iproject.collect(dirsFailed)

                # raise an error in case distribution failed for some users
                if dirsFailed:
                    dirsStr = ", ".join(dirsFailed)
                    MODULE.info("Failed collecting the following dirs: %s" % dirsStr)
                    raise IOError(
                        _("The following user directories could not been collected: %s") % dirsStr
                    )

                # save result
                result.append({"name": iid, "success": True})
            except (ValueError, IOError) as exc:
                result.append({"name": iid, "success": False, "details": str(exc)})

        # return the results
        self.finished(request.id, result)

    @sanitize(StringSanitizer(required=True))
    def adopt(self, request):
        # try to open the UDM user object of the current user
        sender = self._get_sender(request)

        # update the sender information of the selected projects
        result = []
        for iid in request.options:
            try:
                # make sure that project could be loaded
                iproject = util.Project.load(iid)
                if not iproject:
                    raise IOError(_('Project "%s" could not be loaded') % iid)

                # project was loaded successfully
                iproject.sender = sender
                iproject.save()
            except (ValueError, IOError) as exc:
                result.append({"name": iid, "success": False, "details": str(exc)})

        # return the results
        self.finished(request.id, result)

    @sanitize(DictSanitizer({"object": StringSanitizer(required=True)}, required=True))
    def remove(self, request):
        """Removes the specified projects"""
        for iproject in [util.Project.load(ientry.get("object")) for ientry in request.options]:
            if not iproject:
                continue

            # make sure that only the project owner himself (or an admin) is able
            # to see the content of a project
            if request.flavor == "teacher" and not compare_dn(iproject.sender.dn, request.user_dn):
                raise UMC_Error(
                    _("Only the owner himself or an administrator may delete a project."),
                    status=403,
                )

            # purge the project
            iproject.purge()

        self.finished(request.id, None)
