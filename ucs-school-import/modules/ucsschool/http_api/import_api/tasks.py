#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2025 Univention GmbH
#
# https://www.univention.de/
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

"""Celery tasks"""

#
# To monitor the celery queue run in an ncurses terminal UI:
#    celery --app=ucsschool.http_api.app.celery:app control enable_events
#    celery --app=ucsschool.http_api.app.celery:app events
#

from __future__ import unicode_literals

import itertools
import logging
import pathlib
import shutil
import time
import traceback

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django_celery_results.models import TaskResult

from ucsschool.importer.exceptions import (
    InitialisationError,
    UcsSchoolImportError,
    UcsSchoolImportFatalError,
)
from univention.config_registry import ucr

from .constants import JOB_ABORTED, JOB_FINISHED, JOB_SCHEDULED, JOB_STARTED
from .http_api_import_frontend import HttpApiImportFrontend
from .models import Logfile, PasswordsFile, SummaryFile, UserImportJob

IMPORT_JOB_BASEDIR = pathlib.Path(settings.UCSSCHOOL_IMPORT["import_jobs_basedir"]).resolve()
logger = get_task_logger(__name__)
logger.level = logging.DEBUG
logging.root.setLevel(
    logging.INFO
)  # someone sets this to DEBUG, and then we catch all of Djangos SQL queries!


def run_import_job(task, importjob_id):
    try:
        importjob = UserImportJob.objects.get(pk=importjob_id)
    except ObjectDoesNotExist as exc:
        logger.exception(str(exc))
        raise
    timeout = 10
    while importjob.status != JOB_SCHEDULED:
        # possible race condition: we write JOB_STARTED into DB before client
        # (UserImportJobSerializer) writes JOB_SCHEDULED into DB
        time.sleep(1)
        importjob.refresh_from_db()
        timeout -= 1
        if timeout <= 0:
            raise InitialisationError("{} did not reach JOB_SCHEDULED state in 60s.".format(importjob))
    runner = HttpApiImportFrontend(importjob, task, logger)
    importjob.log_file = Logfile.objects.create(path=runner.logfile_path)
    importjob.password_file = PasswordsFile.objects.create(path=runner.password_file)
    importjob.summary_file = SummaryFile.objects.create(path=runner.summary_file)
    importjob.status = JOB_STARTED
    runner.update_job_state(description="Initializing: 0%.")
    try:
        task_result = TaskResult.objects.get(task_id=importjob.task_id)
        importjob.result = task_result
    except ObjectDoesNotExist:
        logger.error(
            "Cannot find TaskMeta object after running update_job_state() for import job {!r}.".format(
                importjob
            )
        )

    importjob.save(update_fields=("log_file", "password_file", "result", "status", "summary_file"))

    logger.info("-- Preparing import job... --")
    success = False
    try:
        runner.prepare_import()
    except Exception as exc:
        # log.exception unless it's a InitialisationError with a 'log_traceback' attribute set to False
        if getattr(exc, "log_traceback", True):
            log = logger.exception
        else:
            log = logger.error
        log("An error occurred while preparing the import job: {}".format(exc))
    else:
        # from here on we can log with the import logger
        runner.logger.info("-- Starting import job... --")
        try:
            runner.do_import()
            success = True
        except UcsSchoolImportError as exc:
            runner.errors.append(exc)
        except Exception as exc:
            runner.errors.append(
                UcsSchoolImportFatalError("An unknown error terminated the import job: {}".format(exc))
            )
            runner.logger.error(
                "An unknown error terminated the import job: {}\n{}".format(
                    exc, "".join(traceback.format_exc())
                )
            )
        runner.logger.info("-- Finished import. --")

    importjob = UserImportJob.objects.get(pk=importjob_id)
    importjob.status = JOB_FINISHED if success else JOB_ABORTED
    importjob.save(update_fields=("status",))
    return success, "{}\n{}".format(
        runner.user_import_summary_str, "\n".join(str(err) for err in runner.errors)
    )


def cleanup_import_jobs():
    """Delete old stopped import jobs if ucsschool/import/http_api/import_jobs_to_keep is set."""
    max_import_jobs = ucr.get_int("ucsschool/import/http_api/import_jobs_to_keep")
    if max_import_jobs <= 0:
        return

    all_stopped_non_dryrun_jobs = UserImportJob.objects.filter(
        (Q(status=JOB_ABORTED) | Q(status=JOB_FINISHED)) & Q(dryrun=False)
    ).order_by("-date_created")

    all_stopped_dryrun_jobs = UserImportJob.objects.filter(
        (Q(status=JOB_ABORTED) | Q(status=JOB_FINISHED)) & Q(dryrun=True)
    ).order_by("-date_created")

    if (
        all_stopped_non_dryrun_jobs.count() <= max_import_jobs
        and all_stopped_dryrun_jobs.count() <= max_import_jobs
    ):
        return

    logger.info("Cleaning up old import jobs.")
    jobs_to_delete = all_stopped_non_dryrun_jobs[max_import_jobs:]
    dry_run_jobs_to_delete = all_stopped_dryrun_jobs[max_import_jobs:]
    logger.info(
        f"Removing {jobs_to_delete.count()} import and {dry_run_jobs_to_delete.count()} dry run jobs."
    )
    for job in itertools.chain(jobs_to_delete, dry_run_jobs_to_delete):
        path = pathlib.Path(job.basedir).resolve()
        try:
            if (
                path.exists()
                and path.is_dir()
                and path.is_relative_to(IMPORT_JOB_BASEDIR)
                and path != IMPORT_JOB_BASEDIR
            ):
                logger.info(f"Removing folder {path} of {job=!s}")
                shutil.rmtree(path)
        except Exception as exc:
            logger.error(f"Error during removal of folder {path} of {job=}:\n{exc}")

        job.delete()
    logger.info("Finished cleanup_import_jobs.")


@shared_task(bind=True)
def import_users(self, importjob_id):
    logger.info("Starting UserImportJob %d (%r).", importjob_id, self)
    success, summary_str = run_import_job(self, importjob_id)
    logger.info("Finished UserImportJob %d.", importjob_id)
    try:
        cleanup_import_jobs()
    except Exception as exc:
        logger.error("Error during cleanup_import_jobs(): %s", exc)
    return HttpApiImportFrontend.make_job_state(
        description="UserImportJob #{} ended {}.\n\n{}".format(
            importjob_id, "successfully" if success else "with error", summary_str
        ),
        percentage=100,
    )


@shared_task(bind=True)
def dry_run(self, importjob_id):
    logger.info("Starting dry run %d (%r).", importjob_id, self)
    success, summary_str = run_import_job(self, importjob_id)
    logger.info("Finished dry run %d.", importjob_id)
    return HttpApiImportFrontend.make_job_state(
        description="UserImportJob #{} (dry run) ended {}.\n\n{}".format(
            importjob_id, "successfully" if success else "with error", summary_str
        ),
        percentage=100,
    )
