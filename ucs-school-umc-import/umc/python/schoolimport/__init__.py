#!/usr/bin/python3
#
# Univention Management Console
#  Automatic UCS@school user import
#
# Copyright 2017-2024 Univention GmbH
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

import os.path
import shutil
import time

from ucsschool.http_api.client import (
    Client,
    ConnectionError,
    ObjectNotFound,
    PermissionError,
    ServerError,
)
from ucsschool.http_api.import_api.constants import JOB_ABORTED, JOB_FINISHED
from ucsschool.lib.school_umc_base import SchoolBaseModule
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import (
    SimpleThread,
    allow_get_request,
    file_upload,
    require_password,
    sanitize,
    simple_response,
    threaded,
)
from univention.management.console.modules.mixins import ProgressMixin
from univention.management.console.modules.sanitizers import StringSanitizer

_ = Translation("ucs-school-umc-import").translate
CACHE_IMPORT_FILES = "/var/cache/ucs-school-umc-import/"


class Instance(SchoolBaseModule, ProgressMixin):
    def init(self):
        self._progress_objs = {}
        self.client = None

    def get_client(self, request):
        if self.client is not None:
            return self.client

        server = ucr.get("ucsschool/import/http_api/client/server") or "{}.{}".format(
            ucr["hostname"], ucr["domainname"]
        )
        ssl_verify = ucr.is_true("ucsschool/import/http_api/client/ssl_verify", True)
        try:
            request.require_password()
            self.client = Client(
                name=request.username,
                password=request.password,
                server=server,
                log_level=Client.LOG_RESPONSE,
                ssl_verify=ssl_verify,
            )
            return self.client
        except ObjectNotFound:
            raise UMC_Error(
                _(
                    "The UCS@school import API HTTP server could not be reached. It seems it is "
                    "misconfigured, not installed or a proxy/firewall is blocking it."
                ),
                status=503,
            )
        except ServerError as exc:
            raise UMC_Error(
                _("The UCS@school Import API HTTP server is not reachable: %s") % (exc,), status=500
            )

    @require_password
    @simple_response
    def ping(self):
        return True

    @require_password
    @simple_response(with_request=True)
    def schools(self, request):
        schools = [
            {"id": school.name, "label": school.displayName}
            for school in self.get_client(request).school.list()
        ]
        if not schools:
            raise UMC_Error(_("No permissions for running an import for any school."))
        return schools

    @require_password
    @simple_response(with_request=True)
    def userroles(self, request, school):
        if not school:
            return []
        userroles = [
            {"id": role.name, "label": self._parse_user_role(role.name)}
            for role in self.get_client(request).school.get(school).roles
        ]
        if not userroles:
            raise UMC_Error(_("No permissions for running an import for any user role."))
        return userroles

    @require_password
    @file_upload
    def upload_file(self, request):
        filename = request.options[0]["tmpfile"]
        destination = os.path.join(
            CACHE_IMPORT_FILES, "%d-%s" % (time.time(), os.path.basename(request.options[0]["filename"]))
        )
        shutil.move(filename, destination)
        self.finished(request.id, {"filename": os.path.basename(destination)})

    @sanitize(
        filename=StringSanitizer(required=True),
        userrole=StringSanitizer(required=True),
        school=StringSanitizer(required=True),
    )
    @require_password
    @simple_response(with_request=True)
    def dry_run(self, request, filename, userrole, school):
        progress = self.new_progress(total=100)
        thread = SimpleThread(
            "dry run",
            self._dry_run,
            lambda t, r: self.thread_progress_finished_callback(t, r, request, progress),
        )
        thread.run(request, filename, userrole, school, progress)
        return dict(progress.poll(), id=progress.id)

    def _dry_run(self, request, filename, userrole, school, progress):
        progress.progress(True, _("Please wait until the examination of the data is complete."))
        progress.current = 25.0
        progress.job = None
        import_file = os.path.join(CACHE_IMPORT_FILES, os.path.basename(filename))
        try:
            jobid = (
                self.get_client(request)
                .userimportjob.create(
                    filename=import_file, school=school, user_role=userrole, dryrun=True
                )
                .id
            )
        except ConnectionError as exc:
            MODULE.error("ConnectionError during dry-run: %s" % (exc,))
            raise UMC_Error(_("The connection to the import server could not be established."))
        except PermissionError:
            raise UMC_Error(_("The permissions to perform a user import are not sufficient enough."))
        progress.progress(True, _("Examining data..."))
        progress.current = 50.0

        result = {"id": jobid}

        SLEEP_TIME = 0.2
        # default: two minutes (as seconds):
        TIMEOUT_AFTER = int(ucr.get("ucsschool/import/dry-run/timeout", 120)) / SLEEP_TIME
        i = 0
        finished = False
        while not finished:
            i += 1
            if i > TIMEOUT_AFTER:
                raise UMC_Error(_("A time out occurred during examining the data."), result=result)
            time.sleep(SLEEP_TIME)

            try:
                job = self.get_client(request).userimportjob.get(jobid)
            except ConnectionError:
                continue
            finished = job.status in (JOB_FINISHED, JOB_ABORTED)

            if job.result and isinstance(job.result.result, dict):
                progress.progress(True, job.result.result.get("description"))
                progress.current = float(job.result.result.get("percentage", 75.0))
            elif job.status == "Started":
                progress.current = 75.0

        progress.current = 99.0
        if job.status != JOB_FINISHED:
            message = _("The examination of the data failed.")
            message = "%s\n%s" % (message, job.result.result["description"])
            raise UMC_Error(message, result=result)

        return {"summary": job.result.result and job.result.result.get("description")}

    @sanitize(
        filename=StringSanitizer(required=True),
        userrole=StringSanitizer(required=True),
        school=StringSanitizer(required=True),
    )
    @require_password
    @threaded
    def start_import(self, request):
        school = request.options["school"]
        filename = request.options["filename"]
        userrole = request.options["userrole"]
        import_file = os.path.join(CACHE_IMPORT_FILES, os.path.basename(filename))
        try:
            job = self.get_client(request).userimportjob.create(
                filename=import_file, school=school, user_role=userrole, dryrun=False
            )
        except ConnectionError as exc:
            MODULE.error("ConnectionError during import: %s" % (exc,))
            raise UMC_Error(_("The connection to the import server could not be established."))
        except PermissionError:
            raise UMC_Error(_("The permissions to perform a user import are not sufficient enough."))

        os.remove(import_file)
        return {
            "id": job.id,
            "school": job.school.displayName,
            "userrole": self._parse_user_role(job.user_role),
        }

    @require_password
    @simple_response
    def poll_dry_run(self, progress_id):
        progress = self.get_progress(progress_id)
        return progress.poll()

    def get_progress(self, progress_id):
        return self._progress_objs[progress_id]

    @require_password
    @simple_response(with_request=True)
    def jobs(self, request):
        return [
            {
                "id": job.id,
                "school": job.school.displayName,
                "creator": job.principal,
                "userrole": self._parse_user_role(job.user_role),
                "date": job.date_created.isoformat(),
                "status": self._parse_status(job.status),
            }
            for job in self._jobs(request)
        ]

    def _jobs(self, request):
        try:
            return self.get_client(request).userimportjob.list(
                limit=20, dryrun=False, ordering="date_created"
            )
        except ServerError as exc:
            raise UMC_Error(
                _("The UCS@school Import API HTTP server is not reachable: %s") % (exc,), status=500
            )

    def _parse_status(self, status):
        return {
            "New": "new",
            "Scheduled": "scheduled",
            "Started": "started",
            "Finished": "finished",
            "Aborted": "aborted",
        }.get(status, status)

    def _parse_user_role(self, role):
        return {
            "staff": _("Staff"),
            "student": _("Student"),
            "teacher": _("Teacher"),
            "teacher_and_staff": _("Teacher and Staff"),
        }.get(role, role)

    @allow_get_request
    @sanitize(job=StringSanitizer(required=True))
    @require_password
    def get_password(self, request):
        password_file = self.get_client(request).userimportjob.get(request.options["job"]).password_file
        if password_file is not None:
            password_file = password_file.encode("UTF-8")
        self.finished(request.id, password_file, mimetype="text/csv")

    @allow_get_request
    @sanitize(job=StringSanitizer(required=True))
    @require_password
    def get_summary(self, request):
        summary_file = self.get_client(request).userimportjob.get(request.options["job"]).summary_file
        if summary_file is not None:
            summary_file = summary_file.encode("UTF-8")
        self.finished(request.id, summary_file, mimetype="text/csv")
