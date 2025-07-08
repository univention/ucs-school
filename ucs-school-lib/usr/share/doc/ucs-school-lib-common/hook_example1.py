#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2021-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Example hook class that moves the directory of class shares to a backup space,
when they are deleted.

Copy to /usr/share/ucs-school-import/pyhooks to activate it.
"""

import datetime
import os
import shutil

from ucsschool.lib.models.hook import Hook
from ucsschool.lib.models.share import ClassShare

BACKUP_BASE_PATH = "/var/backups/class_shares"


class ClassShareExampleHook(Hook):
    model = ClassShare  # hook will only run for objects of this type
    priority = {
        "pre_create": None,
        "post_create": None,
        "pre_modify": None,
        "post_modify": None,
        "pre_move": None,
        "post_move": None,
        "pre_remove": None,
        "post_remove": 100,  # hook will run after a delete operation
    }

    def post_remove(self, obj):
        """
        Move directory of class share to backup space.

        :param ClassShare obj: the ClassShare instance, that was just deleted from LDAP
        :return: None
        """
        share_path = obj.get_share_path()
        target = os.path.join(
            BACKUP_BASE_PATH,
            "{}_{}".format(
                datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S"), os.path.basename(share_path)
            ),
        )
        if os.path.isdir(share_path):
            if not os.path.isdir(BACKUP_BASE_PATH):
                self.logger.info("Creating backup path %r...", BACKUP_BASE_PATH)
                os.mkdir(BACKUP_BASE_PATH, 0o700)
                os.chown(BACKUP_BASE_PATH, 0, 0)

            self.logger.info("Moving %r of class share %r to %r...", share_path, obj, target)
            shutil.move(share_path, target)
            os.chown(target, 0, 0)
        else:
            self.logger.info("Directory %r of class share %r does not exist.", share_path, obj)
