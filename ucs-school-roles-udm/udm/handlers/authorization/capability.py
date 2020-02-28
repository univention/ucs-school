# -*- coding: utf-8 -*-
#
# Copyright 2020 Univention GmbH
#
# https://www.univention.de/
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
# <https://www.gnu.org/licenses/>.

from univention.admin.layout import Tab, Group
import univention.admin.handlers
import univention.admin.syntax

translation = univention.admin.localization.translation('univention.admin.handlers.ucsschool-capability')
_ = translation.translate

module = 'ucsschool/capability'
childs = False
short_description = _(u'UCS@school capabilty')
object_name = short_description
object_name_plural = _(u'UCS@school capabilties')
long_description = short_description
operations = ['add', 'edit', 'remove', 'search']
default_containers = ['cn=authorization,cn=univention']
help_text = _(u'Check the UCS@school manual')

options = {
	'default': univention.admin.option(
		short_description='',
		default=True,
		objectClasses=['top', 'univentionAuthorizationCapability', ],
	),
}

property_descriptions = {
	'name': univention.admin.property(
		short_description=_(u'Name of the capability'),
		long_description=short_description,
		syntax=univention.admin.syntax.string,
		required=True,
		may_change=False,
		identifies=True,
	),
	'displayName': univention.admin.property(
		short_description=_(u'Display name of the capability'),
		long_description=short_description,
		syntax=univention.admin.syntax.string,
	),
	'description': univention.admin.property(
		short_description=_(u'Description of the capability'),
		long_description=short_description,
		syntax=univention.admin.syntax.string,
	),
}

layout = [
	Tab(_(u'General'), layout=[
		Group(_('Capability settings'), layout=[
			['name', ],
			['displayName', ],
			['description', ],
		]),
	]),
]

mapping = univention.admin.mapping.mapping()
mapping.register('name', 'cn', None, univention.admin.mapping.ListToString)
mapping.register('displayName', 'displayName', None, univention.admin.mapping.ListToString)
mapping.register('description', 'description', None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):
	module = module


lookup = object.lookup
identify = object.identify
