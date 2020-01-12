# Copyright 2020 Univention GmbH
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

import pytest

import ucsschool.kelvin.constants
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.kelvin.import_config import init_ucs_school_import_framework

pytestmark = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)


def test_config_loads():
    init_ucs_school_import_framework()


def test_missing_checks(reset_import_config):
    reset_import_config()
    with pytest.raises(UcsSchoolImportError) as exc_info:
        init_ucs_school_import_framework(configuration_checks=["mapped_udm_properties"])
    assert (
        'Missing "class_overwrites" in configuration checks' in exc_info.value.args[0]
    )
    reset_import_config()
    with pytest.raises(UcsSchoolImportError) as exc_info:
        init_ucs_school_import_framework(configuration_checks=["class_overwrites"])
    assert (
        'Missing "mapped_udm_properties" in configuration checks'
        in exc_info.value.args[0]
    )
    reset_import_config()
    init_ucs_school_import_framework(
        configuration_checks=["mapped_udm_properties", "class_overwrites"]
    )
