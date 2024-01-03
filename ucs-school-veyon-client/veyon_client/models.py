# -*- coding: utf-8 -*-

# Copyright 2020-2024 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import enum as enum
from collections import namedtuple


class VeyonConnectionError(Exception):
    """Raised when communication with the Veyon WebAPI Server is not possible"""


class VeyonError(Exception):
    """Raised when the Veyon WebAPI returns a non-zero error code

    See the official documentation within
    https://docs.veyon.io/en/latest/developer/webapi.html#general
    for possible error codes.
    """

    def __init__(self, message, code):
        super(VeyonError, self).__init__(message)
        self.code = code


class ScreenshotFormat(enum.Enum):
    PNG = "png"
    JPEG = "jpeg"

    def __str__(self):
        return str(self.value)


class AuthenticationMethod(enum.Enum):
    AUTH_KEYS = "0c69b301-81b4-42d6-8fae-128cdd113314"
    AUTH_LDAP = "6f0a491e-c1c6-4338-8244-f823b0bf8670"
    AUTH_LOGON = "63611f7c-b457-42c7-832e-67d0f9281085"
    AUTH_SIMPLE = "73430b14-ef69-4c75-a145-ba635d1cc676"

    def __str__(self):
        return str(self.value)


class Feature(enum.Enum):
    SCREEN_LOCK = "ccb535a2-1d24-4cc1-a709-8b47d2b2ac79"
    INPUT_DEVICE_LOCK = "e4a77879-e544-4fec-bc18-e534f33b934c"
    USER_LOGOFF = "7311d43d-ab53-439e-a03a-8cb25f7ed526"
    REBOOT = "4f7d98f0-395a-4fff-b968-e49b8d0f748c"
    POWER_DOWN = "6f5a27a0-0e2f-496e-afcc-7aae62eede10"
    DEMO_SERVER = "e4b6e743-1f5b-491d-9364-e091086200f4"
    DEMO_CLIENT_FULLSCREEN = "7b6231bd-eb89-45d3-af32-f70663b2f878"
    DEMO_CLIENT_WINDOWED = "ae45c3db-dc2e-4204-ae8b-374cdab8c62c"

    def __str__(self):
        return str(self.value)


VeyonUser = namedtuple("VeyonUser", ["login", "fullName", "session"])
VeyonSession = namedtuple("VeyonSession", ["connection_uid", "valid_until"])
Dimension = namedtuple("Dimension", ["width", "height"])
