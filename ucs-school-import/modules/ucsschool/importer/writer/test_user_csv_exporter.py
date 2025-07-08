#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Class to export test user data from TestUserCreator to CSV."""

from .csv_writer import CsvWriter
from .result_exporter import ResultExporter


class TestUserCsvExporter(ResultExporter):
    field_names = (
        "Schulen",
        "Benutzertyp",
        "Vorname",
        "Nachname",
        "Klassen",
        "Beschreibung",
        "Telefon",
        "EMail",
        "Eltern",
        "Kinder",
    )

    def get_iter(self, user_import):
        # TestUserCreator.make_users() is already a generator
        return user_import

    def get_writer(self):
        return CsvWriter(field_names=self.field_names)

    def serialize(self, user):
        if user["Klassen"]:
            sc = ""
            for school, classes in user["Klassen"].items():
                sc = ",".join([sc, ",".join(["{}-{}".format(school, cls) for cls in classes])])
            user["Klassen"] = sc.strip(",")
        else:
            user["Klassen"] = ""
        user["Schulen"] = ",".join(user["Schulen"])
        for k, v in user.items():
            if not isinstance(v, str):  # py2
                v = v.encode("UTF-8")
            user[k] = v
        return user


class HttpApiTestUserCsvExporter(TestUserCsvExporter):
    field_names = (
        "Schule",
        "Vorname",
        "Nachname",
        "Klassen",
        "Beschreibung",
        "Telefon",
        "EMail",
        "Eltern",
        "Kinder",
    )

    def serialize(self, user):
        if user["Klassen"]:
            if len(user["Klassen"]) > 1:
                raise Exception("Not more than one OU allowed in HTTP API CSV.")
            sc = ""
            for classes in user["Klassen"].values():
                sc = ",".join([sc, ",".join(classes)])
            user["Klassen"] = sc.strip(",")
        else:
            user["Klassen"] = ""
        user["Schule"] = user["Schulen"][0]
        del user["Schulen"]
        del user["Benutzertyp"]
        for k, v in user.items():
            if not isinstance(v, str):  # py2
                v = v.encode("UTF-8")
            user[k] = v
        return user
