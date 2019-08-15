# -*- coding: utf-8 -*-

# Copyright 2019 Univention GmbH
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

import logging
from typing import List
import ruamel.yaml
from univention.admin.client import UDM
from univention.admin.filter import parse as filter_parse, flatten_filter
from .client import Object, Module


logger = logging.getLogger(__name__)


def get_dev_connection():
	with open("/etc/univention/master.secret") as fp:
		return ruamel.yaml.load(fp, Loader=ruamel.yaml.Loader)


def get(name):  # type: (str) -> Module
	"""return UDM module"""
	return UDM.http(**get_dev_connection()).version(0).get(name)


def lookup(module_name, co, lo_udm, filter='', base='', superordinate=None, scope='sub'):
	# type: (...) -> List[Object]
	mod = lo_udm.get(module_name)  # type: Module
	filter_s_parsed = filter_parse(filter)
	if hasattr(filter_s_parsed, "expressions"):
		args = dict((e.variable, e.value) for e in flatten_filter(filter_s_parsed))
	else:
		args = dict(((filter_s_parsed.variable, filter_s_parsed.value),)) if filter_s_parsed.variable else {}
	res = mod.search(filter=args, position=base, scope=scope, superordinate=superordinate, opened=True)
	return list(res)


def init():
	# TODO
	pass
