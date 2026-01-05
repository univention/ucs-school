#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2018-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Configuration checks for SingleSourcePartialImport scenario."""

from ucsschool.importer.exceptions import InitialisationError
from ucsschool.importer.utils.configuration_checks import ConfigurationChecks
from ucsschool.lib.models.school import School


class SingleSourcePartialImportConfigurationChecks(ConfigurationChecks):
    def test_00_required_config_keys(self):
        for attr in ("limbo_ou", "school", "user_role"):
            if not self.config.get(attr):
                raise InitialisationError("No {!r} was specified in the configuration.".format(attr))

    def test_limbo_ou(self):
        if not School(name=self.config["limbo_ou"]).exists(self.lo):
            raise InitialisationError(
                "School {!r} in configuration for 'limbo_ou' does not exist.".format(
                    self.config.get("limbo_ou")
                )
            )

    def test_deactivation_grace(self):
        deactivation_grace = max(
            0, int(self.config.get("deletion_grace_period", {}).get("deactivation", 0))
        )
        if deactivation_grace != 0:
            raise InitialisationError(
                "Value for deletion_grace_period:deactivation is {!r}, must be 0.".format(
                    deactivation_grace
                )
            )

    def test_deletion_grace(self):
        deletion_grace = max(0, int(self.config.get("deletion_grace_period", {}).get("deletion", 0)))
        if deletion_grace == 0:
            self.logger.warning(
                "Very dangerous value for deletion_grace_period:deletion = %d! Expected something "
                "greater than 0.",
                deletion_grace,
            )

    def test_school_not_limbo(self):
        if self.config["school"] == self.config["limbo_ou"]:
            raise InitialisationError(
                "Importing into limbo ({!r}) OU is forbidden.".format(self.config["limbo_ou"])
            )
