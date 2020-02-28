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

translation = univention.admin.localization.translation('univention.admin.handlers.authorization-capability')
_ = translation.translate

module = 'authorization/role'
childs = False
short_description = _(u'Authorization: Role')
object_name = short_description
object_name_plural = _(u'Authorization: Roles')
long_description = short_description
operations = ['add', 'edit', 'remove', 'search']
default_containers = ['cn=authorization,cn=univention']
help_text = _(u'An authorization role may be assigned to users and combines several capabilities.')


options = {
	'default': univention.admin.option(
		short_description='',
		default=True,
		objectClasses=['top', 'univentionAuthorizationRole', ],
	),
}

property_descriptions = {
	'name': univention.admin.property(
		short_description=_(u'Name of the role'),
		long_description=_(u''),
		syntax=univention.admin.syntax.string,
		required=True,
		may_change=False,
		identifies=True,
	),
	'displayName': univention.admin.property(
		short_description=_(u'Display name of the role'),
		long_description=_(u''),
		syntax=univention.admin.syntax.string,
	),
	'description': univention.admin.property(
		short_description=_(u'Description of the role'),
		long_description=_(u''),
		syntax=univention.admin.syntax.string,
	),
	'capability': univention.admin.property(
		short_description=_(u'Capability of the role'),
		long_description=_(u'Capability name of the role'),
		multivalue=True,
		syntax=univention.admin.syntax.CapabiltySyntax,
	),
	'isSystemRole': univention.admin.property(
		short_description=_(u'Predefined read only role'),
		long_description=_(u''),
		syntax=univention.admin.syntax.TrueFalseUp,
		required=True,
		default='FALSE',
		may_change=False,
	),
}

layout = [
	Tab(_(u'General'), layout=[
		Group(_('Role settings'), layout=[
			['name', ],
			['displayName', 'systemRole'],
			['description', ],
			['capability', ],
		]),
	]),
]


def mapLinkValue(vals):
	return [univention.admin.syntax.CapabiltySyntax.delimiter.join(val) for val in vals]


def unmapLinkValue(vals):
	return [val.split(univention.admin.syntax.CapabiltySyntax.delimiter) for val in vals]


mapping = univention.admin.mapping.mapping()
mapping.register('name', 'cn', None, univention.admin.mapping.ListToString)
mapping.register('displayName', 'displayName', None, univention.admin.mapping.ListToString)
mapping.register('description', 'description', None, univention.admin.mapping.ListToString)
mapping.register('capability', 'univentionAuthCapability', mapLinkValue, unmapLinkValue)
mapping.register('systemRole', 'univentionAuthIsSystemRole', None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):
	module = module


lookup = object.lookup
identify = object.identify
