# -*- coding: utf-8 -*-

# TODO: remove when ucsschool.lib is fixed
#
# currently ucsschool.lib needs udm_modules.init() before getting imported,
# when using extended attributes

from ucsschool.importer.utils.ldap_connection import get_admin_connection
import univention.admin.modules as udm_modules

# initialize udm modules before UCSSchoolHelperOptions() hits an extended attribute
connection, position = get_admin_connection()
udm_modules.update()
users_module = udm_modules.get("users/user")
udm_modules.init(connection, position, users_module)
