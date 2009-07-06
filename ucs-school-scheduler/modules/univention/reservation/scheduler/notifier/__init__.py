#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
