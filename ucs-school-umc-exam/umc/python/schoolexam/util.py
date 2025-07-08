#!/usr/bin/python3
#
# Univention Management Console
#  utility code for the UMC exam module
#
# SPDX-FileCopyrightText: 2013-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import logging

import univention.management.console.modules.distribution.util as distribution
from univention.management.console.config import ucr

distribution.DISTRIBUTION_DATA_PATH = ucr.get(
    "ucsschool/exam/cache", "/var/lib/ucs-school-umc-schoolexam"
)
distribution.POSTFIX_DATADIR_SENDER = ucr.get("ucsschool/exam/datadir/sender", "Klassenarbeiten")
distribution.POSTFIX_DATADIR_RECIPIENT = ucr.get("ucsschool/exam/datadir/recipient", "Klassenarbeiten")


class Progress(object):
    def __init__(self, max_steps=100, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.reset(max_steps)

    def reset(self, max_steps=100):
        self._max_steps = max_steps
        self._finished = False
        self._steps = 0
        self._component = ""
        self._info = ""
        self._errors = []

    def poll(self):
        return {
            "finished": self._finished,
            "steps": 100 * float(self._steps) / self._max_steps,
            "component": self._component,
            "info": self._info,
            "errors": self._errors,
        }

    def finish(self):
        self._finished = True

    def component(self, component):
        self._component = component
        self.logger.info(component)

    def info(self, info):
        self.logger.info("%s - %s", self._component, info)
        self._info = info

    def error(self, err):
        self.logger.warning("%s - %s", self._component, err)
        self._errors.append(err)

    def add_steps(self, steps=1):
        self._steps += steps
