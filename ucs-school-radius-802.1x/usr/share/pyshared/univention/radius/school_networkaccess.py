#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school RADIUS 802.1X
#  NTLM-Authentication program
#
# Copyright (C) 2012-2019 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of the software contained in this package
# as well as the source package itself are made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this package provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use the software under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.


from univention.radius.networkaccess import NetworkAccess


class SchoolNetworkAccess(NetworkAccess):

	def __init__(self, *args, **kwargs):
		super(SchoolNetworkAccess, self).__init__(*args, **kwargs)

		self.user_to_group = {}  # { "user_lowercase": ["group1", "group2", ], }
		self.group_info = {}  # { "group1": (23, True, ), }
		self.log_target = None
		self.load_info()

	def load_info(self):
		self.logger.debug('Loading proxy rules from ucr')
		for key in self.configRegistry:
			if key.startswith('proxy/filter/usergroup/'):
				group = key[len('proxy/filter/usergroup/'):]
				users = self.configRegistry[key].split(',')
				for user in users:
					self.user_to_group.setdefault(user.lower(), []).append(group)
			elif key.startswith('proxy/filter/groupdefault/'):
				group = key[len('proxy/filter/groupdefault/'):]
				rule = self.configRegistry[key]
				priority = 0
				try:
					priority = int(self.configRegistry.get('proxy/filter/setting/%s/priority' % (rule, ), ''))
				except ValueError:
					pass
				wlan_enabled = self.configRegistry.is_true('proxy/filter/setting/%s/wlan' % (rule, ))
				if wlan_enabled is not None:
					self.group_info[group] = (priority, wlan_enabled, )
		self.logger.debug('Loaded user_to_group {}'.format(self.user_to_group))
		self.logger.debug('Loaded group_info {}'.format(self.group_info))

	def check_proxy_filter_policy(self):
		self.logger.debug('Checking proxy rules network access')
		access = self.evaluate_proxy_network_access(self.username)
		if access:
			self.logger.info('Proxy rules allow attempt to login')
		else:
			self.logger.info('Proxy rules deny username attempt to login')
		return access

	def evaluate_proxy_network_access(self, username):
		groups = self.user_to_group.get(username.lower())
		if groups is None:
			self.logger.debug('DENY: No proxy rules for user {} found'.format(username))
			return False
		matching_groups = {group: info for group, info in self.group_info.iteritems() if group in groups}
		if not matching_groups:
			self.logger.debug('DENY: user {} not found in any WLAN enabled group'.format(username))
			self.logger.debug('DENY: user {} groups={}'.format(groups))
			self.logger.debug('DENY: WLAN enabled groups={}'.format(self.group_info.keys()))
			return False
		max_priority = max(rule[0] for rule in matching_groups.values())
		max_priority_groups = {group: info for group, info in matching_groups.iteritems() if info[0] == max_priority}
		if any(wlan_enabled for priority, wlan_enabled in max_priority_groups.values()):
			self.logger.debug('ALLOW: WLAN is enabled in a group with highest priority (maxPriorityGroups={})'.format(max_priority_groups))
			return True
		self.logger.debug('DENY: WLAN is not enabled in any group with highest priority (maxPriorityGroups={})'.format(max_priority_groups))
		return False
