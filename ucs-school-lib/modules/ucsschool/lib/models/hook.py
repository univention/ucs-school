#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2021-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Base class for all Python based hooks for ucsschool.lib.model classes derived
from UCSSchoolHelperAbstractClass.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Type, Union  # noqa: F401

from ..pyhooks.pyhook import PyHook
from .utils import ucr

if TYPE_CHECKING:
    from ucsschool.lib.models.base import UCSSchoolHelperAbstractClassTV  # noqa: F401
    from univention.admin.uldap import access as LoType  # noqa: F401
    from univention.config_registry import ConfigRegistry  # noqa: F401


class Hook(PyHook):
    """
    Base class for all (1) Python based hooks for ucsschool.lib.model classes
    derived from UCSSchoolHelperAbstractClass.

    The :py:attr:`model` attribute must be set to the class object the hook is
    intended for.

    Examples are provided in /usr/share/doc/ucs-school-lib-common/hook_example*.py

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

    def __init__(self, lo, *args, **kwargs):  # type: (LoType, *Any, **Any) -> None
        super(Hook, self).__init__(*args, **kwargs)

        from .base import UCSSchoolHelperAbstractClass  # prevent circular dependency

        try:
            # issubclass will raise TypeError if self.model is not a class object
            if not issubclass(self.model, UCSSchoolHelperAbstractClass):
                raise TypeError
        except TypeError:
            raise TypeError('Hooks "model" attribute must be a ucsschool.lib.model class object.')

        self.lo = lo  # type: LoType
        self.logger = logging.getLogger("ucsschool.lib.hook.{}".format(self.__class__.__name__))  # type: logging.Logger
        self.ucr = ucr  # type: ConfigRegistry
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
