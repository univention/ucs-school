#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school lib
#  module: UCS@school i18n
#
# SPDX-FileCopyrightText: 2014-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from ucsschool.lib.roles import role_legal_guardian, role_pupil, role_staff, role_teacher

ucs_school_l10n_languages_de = {
    role_pupil: "schueler",
    role_teacher: "lehrer",
    role_staff: "mitarbeiter",
    role_legal_guardian: "sorgeberechtigte",
}

ucs_school_l10n_languages = {
    "de": ucs_school_l10n_languages_de,
}


def ucs_school_name_i18n(name, lang="de"):
    """i18n function for localization of UCS@school standard names"""
    # return _(name)  # this would be simple..
    if lang in ucs_school_l10n_languages:
        return ucs_school_l10n_languages[lang].get(name, name)
    else:
        return name
