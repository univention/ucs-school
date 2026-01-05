#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Write the passwords of newly created users to a CSV file."""

import itertools

from ..factory import Factory
from ..models.import_user import ImportUser
from ..writer.result_exporter import ResultExporter


class NewUserPasswordCsvExporter(ResultExporter):
    """Export passwords of new users to a CSV file."""

    field_names = ("username", "password", "role", "lastname", "firstname", "schools", "classes")

    def __init__(self, *arg, **kwargs):
        super(NewUserPasswordCsvExporter, self).__init__(*arg, **kwargs)
        self.factory = Factory()
        self.a_user = self.factory.make_import_user([])

    def get_iter(self, user_import):
        """Return only the new users."""
        li = list(itertools.chain(*user_import.added_users.values()))
        li.sort(key=lambda x: int(x["entry_count"]) if isinstance(x, dict) else int(x.entry_count))
        return li

    def get_writer(self):
        """Use the user result csv writer."""
        return self.factory.make_user_writer(field_names=self.field_names)

    def serialize(self, user):
        if isinstance(user, ImportUser):
            pass
        elif isinstance(user, dict):
            user = self.a_user.from_dict(user)
        else:
            raise TypeError(
                "Expected ImportUser or dict but got {}. Repr: {}".format(type(user), repr(user))
            )

        return {
            "username": user.name,
            "password": user.password,
            "role": user.role_sting,
            "lastname": user.lastname,
            "firstname": user.firstname,
            "schools": ",".join(user.schools),
            "classes": user.school_classes_as_str,
        }
