# -*- coding: utf-8 -*-
#
# Copyright 2017-2020 Univention GmbH
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
# you and Univention.
#
# This program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.
#
from __future__ import absolute_import

import os
import subprocess

from univention.listener import ListenerModuleHandler

name = "clean_exam_homedirs"


class CleanupHomedirHandler(ListenerModuleHandler):
    class Configuration(object):
        name = name
        description = "Removes directories of disabled exam-students."
        ldap_filter = "(objectClass=ucsschoolExam)"
        attributes = ["ucsschoolRole"]

    def __init__(self, listener_configuration, *args, **kwargs):
        super(CleanupHomedirHandler, self).__init__(listener_configuration, *args, **kwargs)
        self.exam_auto_remove = self.ucr.is_true("ucsschool/exam/user/homedir/autoremove", False)

    def dir_exists(self, dir):
        if os.path.exists(dir) and os.path.isdir(dir):
            return True
        else:
            self.logger.warning("{} is not a directory".format(dir))
            return False

    def remove_files_in_dir(self, dn, src):
        if not self.dir_exists(src):
            return
        with self.as_root():
            try:
                subprocess.call("rm -rf {}/*".format(src), shell=True)
                # shutil.rmtree(src)  # [Errno 1] Operation not permitted
                self.logger.info("removed {}.".format(src))
            except EnvironmentError as exc:
                ret = str(exc)
                self.logger.warning("failed remove home of {} from {}: {}".format(dn, src, ret))

    def modify(self, dn, old, new, old_dn):
        self.logger.info("dn: %r", dn)
        diff = self.diff(old, new, keys=["ucsschoolRole"])
        if diff:
            old_roles, new_roles = diff["ucsschoolRole"]
            old_exam_role_set = [True for role in old_roles if role.startswith("exam_user:exam:")]
            new_exam_role_set = [True for role in new_roles if role.startswith("exam_user:exam:")]
            if not new_exam_role_set and old_exam_role_set:
                home_dir = old.get("homeDirectory", [None])[0]
                if self.exam_auto_remove and home_dir:
                    self.remove_files_in_dir(dn, home_dir)
