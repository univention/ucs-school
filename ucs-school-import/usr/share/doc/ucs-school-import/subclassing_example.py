#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2024 Univention GmbH
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
#
# This is an example of how advanced modifications can be made to the import
# code.
#
# 1. Subclass the classes whose code need modification.
# 2. Tell the default factory to use your class instead of the standard class.
#
#    See user_import_configuration_readme.txt for a list of classes that can be
#    replaced like this. Below is an example of how to change the configuration
#    and for a subclass.
#
#    The DefaultUserImportFactory code can be found in
#    /usr/lib/python3/dist-packages/ucsschool/importer/default_user_import_factory.py
#

#
# Store your class (in the example it is _this_ file) somewhere it is found
# by the system Python installation:
# mkdir -p /usr/local/lib/python3/dist-packages
# cp /usr/share/doc/ucs-school-import/subclassing_example.py /usr/local/lib/python3/dist-packages
#
# Test with:
# python3 -c 'from subclassing_example import MyUserImport'
# (Output should be none - at least no ImportError.)
#
# Then change the configuration like this:
# (Replace "/var/lib/ucs-school-import/configs/myconfig.json" with your actual
# configuration file and "subclassing_example.MyUserImport" with your module.class.)
#
# python3 -c 'MYCFG="/var/lib/ucs-school-import/configs/myconfig.json"; import json; cnf=json.load(open(MYCFG, "rb")); cnf["classes"]=cnf.get("classes", {}); cnf["classes"]["user_importer"]="subclassing_example.MyUserImport"; json.dump(cnf, open(MYCFG+".new", "wb"), indent=4)'  # noqa: E501
#
# Verfiy that /var/lib/ucs-school-import/configs/myconfig.json.new is correct and replace
# /var/lib/ucs-school-import/configs/myconfig.json with it.
#
# The next import run should use the MyUserImport class instead of the
# UserImport class and you should see a line in the logfile directly below the
# configuration dump:
#
# INFO  DefaultUserImportFactory.make_user_importer is now <class 'subclassing_example.MyUserImport'>.
#

import datetime

from ucsschool.importer.mass_import.user_import import UserImport


class MyUserImport(UserImport):
    def do_delete(self, user):
        """
        Delete or deactivate a user.
        IMPLEMENTME to add or change a deletion variant.

        :param ImportUser user: user object
        :return: whether the deletion worked
        :rtype: bool
        """
        if user.birthday == datetime.datetime.now().strftime("%Y-%m-%d"):
            self.logger.info("Not deleting user %s on its birthday!", user)
            return True
        else:
            return super(MyUserImport, self).do_delete(user)
