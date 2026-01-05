#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Base class for all Python based User hooks."""

from typing import TYPE_CHECKING, Dict, Union  # noqa: F401

from .import_pyhook import ImportPyHook

if TYPE_CHECKING:
    from ucsschool.importer.models.import_user import ImportUser  # noqa: F401


class UserPyHook(ImportPyHook):
    """
    Base class for Python based user import hooks.

    An example is provided in /usr/share/doc/ucs-school-import/hook_example.py

    The base class' :py:meth:`__init__()` provides the following attributes:

    * self.dry_run     # whether hook is executed during a dry-run (1)
    * self.lo          # LDAP connection object (2)
    * self.logger      # Python logging instance

    If multiple hook classes are found, hook functions with higher
    priority numbers run before those with lower priorities. None disables
    a function (no need to remove it / comment it out).

    (1) Hooks are only executed during dry-runs, if the class attribute
    :py:attr:`supports_dry_run` is set to `True` (default is `False`). Hooks
    with `supports_dry_run == True` must not modify LDAP objects.
    Therefore the LDAP connection object self.lo will be a read-only connection
    during a dry-run.
    (2) Read-write cn=admin connection in a real run, read-only cn=admin
    connection during a dry-run.
    """

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

    def pre_create(self, user):  # type: (ImportUser) -> None
        """
        Run code before creating a user.

        * The user does not exist in LDAP, yet.
        * `user.dn` is the future DN of the user, if username and school does not change.
        * `user.input_data` contains the (csv) input data, if the user was create during an import job
        * set `priority["pre_create"]` to an `int`, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass

    def post_create(self, user):  # type: (ImportUser) -> None
        """
        Run code after creating a user.

        * The hook is only executed if adding the user succeeded.
        * `user` will be an :py:class:`ImportUser`, loaded from LDAP.
        * Do not run :py:meth:`user.modify()`, it will create a recursion. Please use
            :py:meth:`user.modify_without_hooks()`.
        * set `priority["post_create"]` to an int, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass

    def pre_modify(self, user):  # type: (ImportUser) -> None
        """
        Run code before modifying a user.

        * `user` will be a :py:class:`ImportUser`, loaded from LDAP.
        * set `priority["pre_modify"]` to an int, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. :py:class:`ImportUser`)
        :return: None
        """
        pass

    def post_modify(self, user):  # type: (ImportUser) -> None
        """
        Run code after modifying a user.

        * The hook is only executed if modifying the user succeeded.
        * `user` will be an :py:class:`ImportUser`, loaded from LDAP.
        * Do not run :py:meth:`user.modify()`, it will create a recursion. Please use
            :py:meth:`user.modify_without_hooks()`.
        * If running in an import job, the user may not have been removed, but merely deactivated. If
            `user.udm_properties["ucsschoolPurgeTimestamp"]` is set, the user is marked for removal.
        * set `priority["post_modify"]` to an `int`, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass

    def pre_move(self, user):  # type: (ImportUser) -> None
        """
        Run code before changing a users primary school (position).

        * `user` will be an :py:class:`ImportUser`, loaded from LDAP.
        * set `priority["pre_move"]` to an `int`, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass

    def post_move(self, user):  # type: (ImportUser) -> None
        """
        Run code after changing a users primary school (position).

        * The hook is only executed if moving the user succeeded.
        * `user` will be an :py:class:`ImportUser`, loaded from LDAP.
        * Do not run :py:meth:`user.modify()`, it will create a recursion. Please use
            :py:meth:`user.modify_without_hooks()`.
        * set `priority["post_move"]` to an `int`, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass

    def pre_remove(self, user):  # type: (ImportUser) -> None
        """
        Run code before deleting a user.

        * `user` will be an :py:class:`ImportUser`, loaded from LDAP.
        * set `priority["pre_remove"]` to an `int`, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass

    def post_remove(self, user):  # type: (ImportUser) -> None
        """
        Run code after deleting a user.

        * The hook is only executed if the deleting the user succeeded.
        * `user` will be an :py:class:`ImportUser`, loaded from LDAP.
        * The user was removed, do not try to :py:meth:`modify()` it.
        * set `priority["post_remove"]` to an `int`, to enable this method

        :param ImportUser user: User (or a subclass of it, eg. ImportUser)
        :return: None
        """
        pass
