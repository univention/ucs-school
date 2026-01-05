#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2018-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Constants"""

JOB_NEW = "New"
JOB_SCHEDULED = "Scheduled"
JOB_STARTED = "Started"
JOB_ABORTED = "Aborted"
JOB_FINISHED = "Finished"
JOB_STATES = (JOB_NEW, JOB_SCHEDULED, JOB_STARTED, JOB_ABORTED, JOB_FINISHED)
JOB_CHOICES = list(zip(JOB_STATES, JOB_STATES))
