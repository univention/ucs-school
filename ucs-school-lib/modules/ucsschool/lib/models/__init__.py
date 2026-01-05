#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# SPDX-FileCopyrightText: 2014-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import univention.admin.modules as udm_modules
from ucsschool.lib.models import utils  # noqa: F401

from .computer import *  # noqa: F401, F403
from .dhcp import *  # noqa: F401, F403
from .group import *  # noqa: F401, F403
from .misc import *  # noqa: F401, F403
from .network import *  # noqa: F401, F403
from .policy import *  # noqa: F401, F403
from .school import *  # noqa: F401, F403
from .share import *  # noqa: F401, F403
from .user import *  # noqa: F401, F403

udm_modules.update()
