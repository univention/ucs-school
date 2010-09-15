#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Univention GmbH
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

class AbstractEvent (object):
	def __init__ (self, name, obj):
		"""
		@param	name	Name of this even
		@param	obj		Object that belongs to this event
		"""
		self.name = name
		self.obj = obj

class StartEvent (AbstractEvent):
	def __init__ (self, obj):
		"""
		@param	obj		List of Reservation objects that must be started
		"""
		super (StartEvent, self).__init__('start', obj)

class StopEvent (AbstractEvent):
	def __init__ (self, obj):
		"""
		@param	obj		List of Reservation objects that must be stopped
		"""
		super (StopEvent, self).__init__('stop', obj)
