# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2017-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Base class for all Python based exam user hooks.

ATTENTION: These hooks will only be executed by the exam UMC module on the Primary Directory Node!
"""

from ucsschool.importer.utils.import_pyhook import ImportPyHook


class ExamUserPyHook(ImportPyHook):
    """
    See docstring of :py:class:`ucsschool.importer.utils.import_pyhook.ImportPyHook`
    to learn about the attributes available to the hooks methods.
    """

    # If multiple hook classes are found, hook functions with higher
    # priority numbers run before those with lower priorities. None disables
    # a function.
    priority = {
        "pre_create": None,
        # "post_create": None,
        # "pre_remove": None,
        # "post_remove": None,
    }

    def pre_create(self, user_dn, al):
        """
        Run code before creating an exam user.

        * The user does not exist in LDAP, yet.
        * set priority["pre_create"] to an int, to enable this method

        :param user_dn: str: the future DN of the user
        :param al: list of 2-tuples: ldapadd list
        :return: list of 2-tuples: modified ldapadd list
        """
        pass

    # def post_create(self, user):
    # 	"""
    # 	Run code after creating an exam user.
    #
    # 	* The hook is only executed if adding the user succeeded.
    # 	* set priority["post_create"] to an int, to enable this method
    #
    # 	:param user: ExamStudent, loaded from LDAP
    # 	:return: None
    # 	"""
    #
    # def pre_remove(self, user):
    # 	"""
    # 	Run code before deleting an exam user.
    #
    # 	* set priority["post_create"] to an int, to enable this method
    #
    # 	:param user: ExamStudent, loaded from LDAP
    # 	:return: None
    # 	"""
    #
    # def post_remove(self, user):
    # 	"""
    # 	Run code after deleting an exam user.
    #
    # 	* The hook is only executed if deleting the user succeeded.
    # 	* "user" will be an ExamStudent, loaded from LDAP - that does not
    # 	exist anymore - do not modify() it!
    # 	* set priority["post_remove"] to an int, to enable this method
    #
    # 	:param user: ExamStudent
    # 	:return: None
    # 	"""
