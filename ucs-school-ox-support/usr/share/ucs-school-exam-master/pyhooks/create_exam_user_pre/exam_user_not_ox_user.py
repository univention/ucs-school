# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Remove isOxUser flag from Examuser

Depends: ucs-school-umc-exam
"""

from ucsschool.exam.exam_user_pyhook import ExamUserPyHook


class NoOXExamUserPyHook(ExamUserPyHook):
    supports_dry_run = False
    priority = {
        "pre_create": 10,
    }

    def __init__(self, lo=None, dry_run=None, *args, **kwargs):
        # Explicitely pass dry_run=False, so ImportPyHook.__init__() won't
        # have to initialize the import configuration to find out what we
        # already know: it must be dry_run=False, as we'll never run without
        # it: `NoOXExamUserPyHook.supports_dry_run = False`.
        if dry_run is None:
            dry_run = False
        super(NoOXExamUserPyHook, self).__init__(lo, dry_run=dry_run, *args, **kwargs)

    def pre_create(self, user_dn, al):
        """Deactivate OX user flag."""
        for num, (k, v) in enumerate(al):
            if k == "isOxUser" and v == [b"OK"]:
                al[num] = (k, [b"Not"])
                break
        return al
