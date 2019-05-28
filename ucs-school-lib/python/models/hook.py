# -*- coding: utf-8 -*-
#
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

"""
Base class for all Python based hooks for ucsschool.lib.model classes derived
from UCSSchoolHelperAbstractClass.
"""

import logging
from .utils import ucr
from ..pyhooks import PyHook

try:
	from typing import Any, Dict, Union, Type, TypeVar
	UCSSchoolHelperAbstractClassTV = TypeVar(
		'UCSSchoolHelperAbstractClassTV',
		bound='ucsschool.lib.models.base.UCSSchoolHelperAbstractClass'
	)
except ImportError:
	pass


class Hook(PyHook):
	"""
	Base class for all (1) Python based hooks for ucsschool.lib.model classes
	derived from UCSSchoolHelperAbstractClass.

	The :py:attr:`model` attribute must be set to the class object the hook is
	entended for.

	An example is provided in /usr/share/doc/python-ucs-school/hook_example.py

	The following attributes are available:

	* self.lo        # LDAP connection object
	* self.logger    # Python logging instance
	* self.ucr       # UCR instance

	If multiple hook classes are found, hook methods with higher priority
	numbers run before those with lower priorities. None disables a method (no
	need to remove it or comment it out).

	(1) While it also works for :py:class:`ucsschool.importer.models.import_user.ImportUser`,
	it is strongly recommended to use the dedicated hook class
	:py:class:`ucsschool.importer.utils.user_pyhook.UserPyHook` for it. It adds
	attributes that are useful in the user import context.
	"""

	model = None  # type: Type[UCSSchoolHelperAbstractClassTV]
	priority = {
		"pre_create": None,
		"post_create": None,
		"pre_modify": None,
		"post_modify": None,
		"pre_move": None,
		"post_move": None,
		"pre_remove": None,
		"post_remove": None,
	}  # type: Dict[str, Union[int, None]]

	def __init__(self, lo, *args, **kwargs):  # type: (univention.admin.uldap.access, *Any, **Any) -> None
		super(Hook, self).__init__(*args, **kwargs)

		from .base import UCSSchoolHelperAbstractClass  # prevent adding circular dependeny for this check
		try:
			# issubclass will raise TypeError if self.model is not a class object
			if not issubclass(self.model, UCSSchoolHelperAbstractClass):
				raise TypeError
		except TypeError:
			raise TypeError('Hooks "model" attribute must be a ucsschool.lib.model class object.')

		self.lo = lo  # type: univention.admin.uldap.access
		self.logger = logging.getLogger('ucsschool.lib.hook.{}'.format(self.__class__.__name__))  # type: logging.Logger
		self.ucr = ucr  # type: univention.config_registry.ConfigRegistry
		self.model.hook_init(self)

	def pre_create(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code before creating an object.

		* The object does not exist in LDAP, yet.
		* `obj.dn` is the future DN of the obj, if objname and school does not change.
		* set `priority["pre_create"]` to an `int`, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def post_create(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code after creating an object.

		* The hook is only executed if adding the object succeeded.
		* Do *not* run :py:meth:`obj.modify()`, it will create a recursion. If
			you must modify the object use :py:meth:`obj.modify_without_hooks()`.
		* set `priority["post_create"]` to an int, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def pre_modify(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code before modifying an object.

		* set `priority["pre_modify"]` to an int, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def post_modify(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code after modifying an object.

		* The hook is only executed if modifying the object succeeded.
		* Do *not* run :py:meth:`obj.modify()`, it will create a recursion. If
			you must modify the object use :py:meth:`obj.modify_without_hooks()`.
		* set `priority["post_modify"]` to an `int`, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def pre_move(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code before changing an objects position in the LDAP tree. This
		usually happens when modifying the primary school
		(:py:attr:`obj.school`).

		* set `priority["pre_move"]` to an `int`, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def post_move(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code before changing an objects position in the LDAP tree. This
		usually happens when modifying the primary school
		(:py:attr:`obj.school`).

		* The hook is only executed if moving the object succeeded.
		* Do *not* run :py:meth:`obj.modify()`, it will create a recursion. If
			you must modify the object use :py:meth:`obj.modify_without_hooks()`.
		* set `priority["post_move"]` to an `int`, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def pre_remove(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code before deleting an object.

		* set `priority["pre_remove"]` to an `int`, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass

	def post_remove(self, obj):  # type: (UCSSchoolHelperAbstractClassTV) -> None
		"""
		Run code after deleting an object.

		* The hook is only executed if the deleting the object succeeded.
		* The object was removed, do not try to :py:meth:`modify()` it.
		* set `priority["post_remove"]` to an `int`, to enable this method

		:param base.UCSSchoolHelperAbstractClass obj: ucsschool.lib.model object
		:return: None
		"""
		pass
