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

# TODO: setting.delete () does not cause [reservation|profile].options to be invalidated
# TODO: enable different sql-backends: sqlite, postgresql, mysql (default)

import sys

import MySQLdb

WAITING = 'WAITING'
ACTIVE = 'ACTIVE'
ERROR = 'ERROR'
DONE = 'DONE'

RESERVATION_TABLE = 'reservation'
PROFILE_TABLE = 'resprofiles'
SETTINGS_TABLE = 'ressettings'
PROFOPTREL_TABLE = 'profoptrel'
RESOPTREL_TABLE = 'resoptrel'
VACATION_TABLE = 'vacations'
LESSONTIME_TABLE = 'lessontimes'
APPLICATIONS_TABLE = 'swlicenses'

CONNECTION = None

##### Helper functions
def Property (func):
	return property(doc=func.__doc__, **func())

def buildUpdateStatement (clauseTillSet, params, where_params):
	statement = clauseTillSet
	new_params = []
	first = True
	for (k, v) in params.items ():
		new_params.append (v)
		if first:
			first = False
			statement += ' %s=%%s' % k
		else:
			statement += ', %s=%%s' % k
	res = buildSelectStatement (statement + ' WHERE', where_params)
	return (res[0], new_params + res[1])

def buildInsertStatement (clauseTillSet, params):
	statement = clauseTillSet
	new_params = []
	first = True
	for (k, v) in params.items ():
		new_params.append (v)
		if first:
			first = False
			statement += ' %s=%%s' % k
		else:
			statement += ', %s=%%s' % k
	return (statement, new_params)

def buildSelectStatement (clauseTillWhere, params):
	statement = clauseTillWhere
	new_params = []
	first = True
	for (k, v) in params.items ():
		if v == None:
			if first:
				first = False
				statement += ' %s IS NULL' % k
			else:
				statement += ' AND %s IS NULL' % k
		else:
			new_params.append (v)
			if first:
				first = False
				statement += ' %s=%%s' % k
			else:
				statement += ' AND %s=%%s' % k
	return (statement, new_params)

def disconnect ():
	global CONNECTION
	CONNECTION.close ()
	CONNECTION = None

def connect (*args, **kwargs):
	global CONNECTION
	if not CONNECTION:
		CONNECTION = MySQLdb.connect(*args, **kwargs)
		if CONNECTION.get_server_info() >= '4.1' and not CONNECTION.character_set_name().startswith('utf8'):
			CONNECTION.set_character_set('utf8')
	return CONNECTION


##### Exceptions
class DBSelectFaild (Exception):
	def __init__ (self, msg):
		self.msg = msg

class ConnectionNotAvailable (Exception):
	def __init__ (self, msg='Database connection not available'):
		self.msg = msg

class IllegalRelation (Exception):
	def __init__ (self, msg):
		self.msg = msg

class InsufficientRelations (Exception):
	def __init__ (self, msg):
		self.msg = msg

##### DB-Object classes
class Reservation (object):
	# this list of class attributes serves as API for the UMC module
	ROWS = ['reservationID', 'name', 'description', 'owner', 'hostgroup', 'usergroup', 'startTime', 'endTime', 'iterationDays', 'iterationEnd', 'iterateVacations', 'resprofileID', 'status', 'replacedByID']

	def __init__ (self):
		self.id = None
		self.name = None
		self.description = None
		self.owner = None
		self.hostgroup = None
		self.usergroup = None
		self.startTime = None
		self.endTime = None
		self.iterationDays = None
		self.iterationEnd = None
		self.iterateInVacations = None
		self.status = None
		self.replacedByID = None

		self._resprofileID = None
		self._profile = None
		self._options = None

		self.setWaiting () # default value for status

	def validate (self):
		"""
		Validates object values
		"""
		assert self.name != None
		if self.startTime or self.endTime:
			assert self.startTime != None
			assert self.endTime != None
			# assert self.startTime < self.endTime
		return True

	def reload (self):
		if not self.id:
			raise ValueError ('Id must be set.')
		r = Reservation.get (self.id)
		if not r:
			raise ValueError ('Unable to find Reservation with id: %d' % self.id)
		self.name = r.name
		self.description = r.description
		self.owner = r.owner
		self.hostgroup = r.hostgroup
		self.usergroup = r.usergroup
		self.startTime = r.startTime
		self.endTime = r.endTime
		self.iterationDays = r.iterationDays
		self.iterationEnd = r.iterationEnd
		self.iterateInVacations = r.iterateInVacations
		self.status = r.status
		self.replacedByID = r.replacedByID
		self.resprofileID = r.resprofileID
		self._profile = None
		self._options = None

	@Property
	def reservationID ():
		def fget (self):
			return self.id
		def fset (self, _id):
			self.id = _id
		return locals ()

	@Property
	def resprofileID ():
		def fget (self):
			return self._resprofileID
		def fset (self, _id):
			if _id == None:
				self._resprofileID = None
				self._profile = None
			elif self._resprofileID != _id:
				self._resprofileID = _id
				if self._profile and self._profile.id != _id:
					self._profile = None
		return locals ()

	@Property
	def profile ():
		def fget (self):
			if self._profile == None and self.resprofileID != None:
				self._profile = Profile.get (self.resprofileID)
			return self._profile
		def fset (self, profile):
			if profile == None:
				self._profile = None
				self.resprofileID = None
			elif profile.id == None:
				raise InsufficientRelations ('Can not relate to a Profile that is not stored in the database. Please save it first')
			else:
				self._profile = profile
				self.resprofileID = profile.id
		return locals ()

	@Property
	def options ():
		def fget (self):
			if self._options == None:
				if not CONNECTION:
					raise ConnectionNotAvailable ()
				cursor = CONNECTION.cursor ()
				cursor.execute ("SELECT * FROM %s WHERE reservationID=%%s" % RESOPTREL_TABLE, (self.id, ))
				self._options = []
				for res in cursor.fetchall ():
					o = Option.get (res[0], self)
					if o:
						self._options.append (o)
				cursor.close ()
			return self._options
		return locals ()

	@classmethod
	def get (cls, _id, resolveReplacement=True):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE reservationID=%%s" % RESERVATION_TABLE, (_id, ))
		res = cursor.fetchone ()
		if res:
			# resolve replacedByID
			if resolveReplacement and res[13]:
				_newid = res[13]
				cursor.close ()
				return Reservation.get (_newid)
			r = Reservation ()
			r.id = res[0]
			r.name = res[1]
			r.description = res[2]
			r.owner = res[3]
			r.hostgroup = res[4]
			r.usergroup = res[5]
			r.startTime = res[6]
			r.endTime = res[7]
			r.iterationDays = res[8]
			r.iterationEnd = res[9]
			r.iterateInVacations = res[10]
			r.resprofileID = res[11]
			r.status = res[12]
			if not resolveReplacement:
				r.replacedByID = res[13]
			else:
				r.replacedByID = None
			cursor.close ()
			return r
		cursor.close ()

	def delete (self):
		"""
		Deletes Reservation and related Options from DB
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			cursor = CONNECTION.cursor ()
			# delete relations
			for o in self.options:
				if o: o.delete ()
			#cursor.execute ("DELETE FROM %s WHERE reservationID=%%s" % RESOPTREL_TABLE, (self.id, ))
			# delete reservation
			cursor.execute ("DELETE FROM %s WHERE reservationID=%%s" % RESERVATION_TABLE, (self.id, ))
			cursor.close ()
			self.id = None
			self._options = None

	def relateToSetting (self, setting):
		"""
		If this relation already exists, it return the existing Option,
		otherwise a new (unsaved) Option is created
		"""
		for opt in self.options:
			if opt.ressettingID == setting.id:
				return opt
		if self._options == None:
			self._options = []
		option = Option (self)
		option.setting = setting
		self._options.append (option)
		return option

	def _getParams (self):
		return {'name':self.name,
				'description':self.description,
				'owner':self.owner,
				'hostgroup':self.hostgroup,
				'usergroup':self.usergroup,
				'startTime':self.startTime,
				'endTime':self.endTime,
				'iterationDays':self.iterationDays,
				'iterationEnd':self.iterationEnd,
				'iterateInVacations':self.iterateInVacations,
				'resprofileID':self.resprofileID,
				'status':self.status,
				'replacedByID':self.replacedByID}

	def save (self):
		"""
		Saves Reservation to DB

		WARNING: related Options or Settings are not saved!!
		"""
		if not CONNECTION:
			raise ConnectionNotAvailable ()

		self.validate ()

		cursor = CONNECTION.cursor ()
		if self.id == None:
			# insert new entry
			cursor.execute (*buildInsertStatement ("INSERT %s SET" % RESERVATION_TABLE, self._getParams ()))
			# self.id needs to be updated here
			cursor.close ()
			cursor = CONNECTION.cursor ()
			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % RESERVATION_TABLE, self._getParams ()))
			reslast = cursor.fetchall ()
			if len (reslast) == 0:
				raise DBSelectFaild ('Failed to select previously inserted row. Reservation-Name: %s' % self.name)
			#self.id = reslast[-1][0]
			self.id = reslast[0][0] # hm, the order seems to be the other way around
		else:
			# update existing entry
			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % RESERVATION_TABLE, self._getParams (), {'reservationID':self.id}))
		cursor.close ()

	def isActive (self):
		return self.status == ACTIVE

	def isWaiting (self):
		return self.status == WAITING

	def isError (self):
		return self.status.startswith (ERROR)

	def isDone (self):
		return self.status == DONE

	def setActive (self):
		self.status = ACTIVE
		return self.status

	def setWaiting (self):
		self.status = WAITING
		return self.status

	def setError (self, code):
		self.status = "%s %s" % (ERROR, code)
		return self.status

	def setDone (self):
		self.status = DONE
		return self.status

	def updateStatus (self):
		"""
		Updates status field in DB if Reservation is already stored in database
		(self.id != None)
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			cursor = CONNECTION.cursor ()
			cursor.execute ("UPDATE %s SET status=%%s WHERE reservationID=%%s" % RESERVATION_TABLE, (self.status, self.id))
			cursor.close ()

class Profile (object):
	# this list of class attributes serves as API for the UMC module
	ROWS = ['resprofileID', 'name', 'description', 'owner', 'isglobaldefault']

	def __init__ (self):
		self.id = None
		self.name = None
		self.description = None
		self.owner = None
		self.isglobaldefault = None

		self._options = None

	def reload (self):
		if not self.id:
			raise ValueError ('Id must be set.')
		p = Profile.get (self.id)
		if not p:
			raise ValueError ('Unable to find Profile with id: %d' % self.id)
		self.name = p.name
		self.description = p.description
		self.owner = p.owner
		self.isglobaldefault = p.isglobaldefault
		self._options = None

	@Property
	def resprofileID ():
		def fget (self):
			return self.id
		def fset (self, _id):
			self.id = _id
		return locals ()

	@Property
	def options ():
		def fget (self):
			if self._options == None:
				if not CONNECTION:
					raise ConnectionNotAvailable ()
				cursor = CONNECTION.cursor ()
				cursor.execute ("SELECT * FROM %s WHERE resprofileID=%%s" % PROFOPTREL_TABLE, (self.id, ))
				self._options = []
				for res in cursor.fetchall ():
					o = Option.get (res[0], self)
					if o:
						self._options.append (o)
				cursor.close ()
			return self._options
		return locals ()

	@classmethod
	def get (cls, _id):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE resprofileID=%%s" % PROFILE_TABLE, (_id, ))
		res = cursor.fetchone ()
		if res:
			p = Profile ()
			p.id = res[0]
			p.name = res[1]
			p.description = res[2]
			p.owner = res[3]
			p.isglobaldefault = res[4]

			cursor.close ()
			return p
		cursor.close ()

	def validate (self):
		"""
		Validates object values
		"""
		assert self.name != None
		return True

	def delete (self):
		"""
		Deletes Profile and related Options from DB
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			cursor = CONNECTION.cursor ()
			# delete relations
			for o in self.options:
				if o: o.delete ()
			#cursor.execute ("DELETE FROM %s WHERE resprofileID=%%s" % PROFOPTREL_TABLE, (self.id, ))
			# delete profile
			cursor.execute ("DELETE FROM %s WHERE resprofileID=%%s" % PROFILE_TABLE, (self.id, ))
			cursor.close ()
			self.id = None
			self._options = None

	def relateToSetting (self, setting):
		"""
		If this relation already exists, it return the existing Option,
		otherwise a new (unsaved) Option is created
		"""
		for opt in self.options:
			if opt.ressettingID == setting.id:
				return opt
		if self._options == None:
			self._options = []
		option = Option (self)
		option.setting = setting
		self._options.append (option)
		return option

	def _getParams (self):
		return {'name':self.name,
				'description':self.description,
				'owner':self.owner,
				'isglobaldefault':self.isglobaldefault}

	def save (self):
		"""
		Saves Profile to DB

		WARNING: related Options or Settings are not saved!!
		"""
		if not CONNECTION:
			raise ConnectionNotAvailable ()

		self.validate ()

		cursor = CONNECTION.cursor ()
		if self.id == None:
			# insert new entry
			cursor.execute (*buildInsertStatement ("INSERT %s SET" % PROFILE_TABLE, self._getParams ()))
			# self.id needs to be updated here
			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % PROFILE_TABLE, self._getParams ()))
			reslast = cursor.fetchall ()
			if len (reslast) == 0:
				raise DBSelectFaild ('Failed to select previously inserted row. Profile-Name: %s' % self.name)
			#self.id = reslast[-1][0]
			self.id = reslast[0][0] # hm, the order seems to be the other way around
		else:
			# update existing entry
			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % PROFILE_TABLE, self._getParams (), {'resprofileID':self.id}))
		cursor.close ()

class Option (object):
	#ROWS = ['profoptrelID', 'ressettingID', 'reservationID', 'value']
	#ROWS = ['resoptrelID', 'ressettingID', 'reservationID', 'value']

	def __init__ (self, relative):
		"""
		relative - either Profile or Reservation but it needs to be a proper object!
		"""
		if not isinstance (relative, Reservation) \
			and not isinstance (relative, Profile):
			raise ValueError ('relative needs to be either a Profile or a Reservation object')
		self.id = None
		self._ressettingID = None
		self.value = None

		self._setting = None
		self._relative = relative

	def reload (self):
		if not (self.id and self.relative):
			raise ValueError ('Id must be set.')
		o = Option.get (self.id, self.relative)
		if not o:
			raise ValueError ('Unable to find Option with id: %d' % self.id)
		self.ressettingID = o.ressettingID
		self.relativeID = o.relativeID
		self.value = o.value

	@Property
	def relativeID ():
		def fget (self):
			return self._relative.id
		def fset (self, _id):
			if _id == None:
				raise ValueError ('Option must be related to a relative!')
			if self._relativeID != _id:
				self._relativeID = _id
				if self._relative.id != _id:
					self._relative = None
		return locals ()

	@Property
	def ressettingID ():
		def fget (self):
			return self._ressettingID
		def fset (self, _id):
			if _id == None:
				raise ValueError ('Option must be related to a setting!')
			if self._ressettingID != _id:
				self._ressettingID = _id
				try:
					if self._setting and self._setting.id != _id:
						self._setting = None
				except:
					print 'uups'
		return locals ()

	@Property
	def setting ():
		def fget (self):
			if self._setting == None and self.ressettingID != None:
				self._setting = Setting.get (self.ressettingID)
			return self._setting
		def fset (self, s):
			if not (s and s.id):
				raise ValueError ('Option must be related to a setting!')
			self._setting = s
			self._ressettingID = s.id
		return locals ()

	@Property
	def relative ():
		def fget (self):
			return self._relative
		return locals ()

	@classmethod
	def get (cls, _id, relative):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		table = None
		idfield = None
		relative_idfield = None
		if isinstance (relative, Reservation) :
			table = RESOPTREL_TABLE
			idfield = 'resoptrelID'
			relative_idfield = 'reservationID'
		elif isinstance (relative, Profile):
			table = PROFOPTREL_TABLE
			idfield = 'profoptrelID'
			relative_idfield = 'resprofileID'

		if table == None or relative_idfield == None:
			raise IllegalRelation (' Option relates in an illegal way to a Setting, Reservation or Profile')

		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE %s=%%s AND %s=%%s" % (table, idfield, relative_idfield), (_id, relative.id))
		res = cursor.fetchone ()
		if res:
			o = Option (relative)
			o.id = res[0]
			o.ressettingID = res[1]
			o.value = res[3]

			cursor.close ()
			return o
		cursor.close ()

	def validate (self):
		"""
		Validates object values
		"""
		assert self.setting != None
		assert self.setting.id != None
		assert self.setting.validate ()
		assert self.relative != None
		assert self.relative.id != None
		assert self.relative.validate ()
		return True

	def delete (self):
		"""
		Deletes Option from DB

		WARNING: related Profiles/Reservations or Settings are not deleted!!
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			if isinstance (self.relative, Reservation):
				table = RESOPTREL_TABLE
				idfield = 'resoptrelID'
			else:
				table = PROFOPTREL_TABLE
				idfield = 'profoptrelID'
			cursor = CONNECTION.cursor ()
			cursor.execute ("DELETE FROM %s WHERE %s=%%s" % (table, idfield), (self.id, ))
			cursor.close ()
			self.id = None

	def _getParams (self):
		if isinstance (self.relative, Reservation):
			idfield = 'reservationID'
		else:
			idfield = 'resprofileID'
		return {'ressettingID':self.ressettingID,
				idfield:self.relativeID,
				'value':self.value}

	def save (self):
		"""
		Saves Option and related items if they are not stored in the database yet

		WARNING: related Profiles/Reservations or Settings are not saved!!
		"""
		if not CONNECTION:
			raise ConnectionNotAvailable ()

		if self.ressettingID == None or self.relativeID == None:
			raise InsufficientRelations ('Can not save Option unless the related Setting and Profile/Reservation is stored in the database')

		self.validate ()

		table = None
		idfield = None
		if self.setting.type.lower () == 'reservation' and isinstance (self.relative, Reservation):
			table = RESOPTREL_TABLE
			idfield = 'resoptrelID'
		elif self.setting.type.lower () == 'profile' and isinstance (self.relative, Profile):
			table = PROFOPTREL_TABLE
			idfield = 'profoptrelID'

		if table == None:
			raise IllegalRelation ('This Option relates in an illegal way to a Setting, Reservation or Profile')

		cursor = CONNECTION.cursor ()
		if self.id == None:
			# insert new entry
			cursor.execute (*buildInsertStatement ("INSERT %s SET" % table, self._getParams ()))
			# self.id needs to be updated here
			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % table, self._getParams ()))
			reslast = cursor.fetchall ()
			if len (reslast) == 0:
				raise DBSelectFaild ('Failed to select previously inserted Option-row')
			#self.id = reslast[-1][0]
			self.id = reslast[0][0] # hm, the order seems to be the other way around
		else:
			# update existing entry
			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % table, self._getParams (), {idfield:self.id}))
		cursor.close ()

class Setting (object):
	#ROWS = ['ressettingID', 'name', 'shortdescription', 'description', 'type', 'ucrStart', 'ucrStop', 'cmdStart', 'cmdStop']

	def __init__ (self):
		self.id = None
		self.name = None
		self.shortdescription = None
		self.description = None
		self.type = None
		self.ucrStart = None
		self.ucrStop = None
		self.cmdStart = None
		self.cmdStop = None

	def validate (self):
		"""
		Validates object values
		"""
		assert self.type != None
		return True

	def reload (self):
		if not self.id:
			raise ValueError ('Id must be set.')
		s = Setting.get (self.id)
		if not s:
			raise ValueError ('Unable to find Setting with id: %d' % self.id)
		self.name = s.name
		self.shortdescription = s.shortdescription
		self.description = s.description
		self.type = s.type
		self.ucrStart = s.ucrStart
		self.ucrStop = s.ucrStop
		self.cmdStart = s.cmdStart
		self.cmdStop = s.cmdStop

	@Property
	def ressettingID ():
		def fget (self):
			return self.id
		def fset (self, _id):
			self.id = _id
		return locals ()

	@classmethod
	def get (cls, _id):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE ressettingID=%%s" % SETTINGS_TABLE, (_id, ))
		res = cursor.fetchone ()
		if res:
			r = Setting ()
			r.id = res[0]
			r.name = res[1]
			r.shortdescription = res[2]
			r.description = res[3]
			r.type = res[4]
			r.ucrStart = res[5]
			r.ucrStop = res[6]
			r.cmdStart = res[7]
			r.cmdStop = res[8]
			cursor.close ()
			return r
		cursor.close ()

	def delete (self):
		"""
		Deletes Setting and Option-relations from DB
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			cursor = CONNECTION.cursor ()
			# delete relations
			if self.type.lower () == 'reservation':
				cursor.execute ("DELETE FROM %s WHERE ressettingID=%%s" % RESOPTREL_TABLE, (self.id, ))
			else:
				cursor.execute ("DELETE FROM %s WHERE ressettingID=%%s" % PROFOPTREL_TABLE, (self.id, ))
			# delete profile
			cursor.execute ("DELETE FROM %s WHERE ressettingID=%%s" % SETTINGS_TABLE, (self.id, ))
			cursor.close ()
			self.id = None

	def relateToRelative (self, relative):
		"""
		If this relation already exists, it return the existing Option,
		otherwise a new (unsaved) Option is created
		"""
		return relative.relateToSetting (self)

	def _getParams (self):
		return {'name':self.name,
				'shortdescription':self.shortdescription,
				'description':self.description,
				'type':self.type,
				'ucrStart':self.ucrStart,
				'ucrStop':self.ucrStop,
				'cmdStart':self.cmdStart,
				'cmdStop':self.cmdStop}

	def save (self):
		"""
		Saves Setting to DB

		WARNING: related Profiles/Reservations or Options are not saved!!
		"""
		if not CONNECTION:
			raise ConnectionNotAvailable ()

		self.validate ()

		cursor = CONNECTION.cursor ()
		if self.id == None:
			# insert new entry
			cursor.execute (*buildInsertStatement ("INSERT %s SET" % SETTINGS_TABLE, self._getParams ()))
			# self.id needs to be updated here
			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % SETTINGS_TABLE, self._getParams ()))
			reslast = cursor.fetchall ()
			if len (reslast) == 0:
				raise DBSelectFaild ('Failed to select previously inserted row. Settings-Name: %s' % self.name)
			#self.id = reslast[-1][0]
			self.id = reslast[0][0] # hm, the order seems to be the other way around
		else:
			# update existing entry
			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % SETTINGS_TABLE, self._getParams (), {'ressettingID':self.id}))
		cursor.close ()

class Application (object):
	#ROWS = ['swID', 'name', 'description', 'actScript', 'deactScript', 'licenses', 'imageActive']

	def __init__ (self):
		self.id = None
		self.name = None
		self.description = None
		self.actScript = None
		self.deactScript = None
		self.licenses = None
		self.imageActive = None

	def reload (self):
		if not self.id:
			raise ValueError ('Id must be set.')
		a = Application.get (self.id)
		if not a:
			raise ValueError ('Unable to find Application with id: %d' % self.id)
		self.name = a.name
		self.description = a.description
		self.actScript = a.actScript
		self.deactScript = a.deactScript
		self.licenses = a.licenses
		self.imageActive = a.imageActive

	@Property
	def swID ():
		def fget (self):
			return self.id
		def fset (self, _id):
			self.id = _id
		return locals ()

	@classmethod
	def get (cls, _id):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE swID=%%s" % APPLICATIONS_TABLE, (_id, ))
		res = cursor.fetchone ()
		if res:
			a = Application ()
			a.id = res[0]
			a.name = res[1]
			a.description = res[2]
			a.actScript = res[3]
			a.deactScript = res[4]
			a.licenses = res[5]
			a.imageActive = res[6]
			cursor.close ()
			return a
		cursor.close ()

#	def delete (self):
#		"""
#		Deletes Application from DB
#		"""
#		if self.id != None:
#			if not CONNECTION:
#				raise ConnectionNotAvailable ()
#			cursor = CONNECTION.cursor ()
#
#			cursor.execute ("DELETE FROM %s WHERE swID=%%s" % APPLICATIONS_TABLE, (self.id, ))
#			cursor.close ()
#			self.id = None
#
#	def _getParams (self):
#		return {'name':self.name,
#				'description':self.description,
#				'actScript':self.actScript,
#				'deactScript':self.deactScript,
#				'licenses':self.licenses,
#				'imageActive':self.imageActive}
#
#	def save (self):
#		"""
#		Saves Application to DB
#		"""
#		if not CONNECTION:
#			raise ConnectionNotAvailable ()
#		cursor = CONNECTION.cursor ()
#		if self.id == None:
#			# insert new entry
#			cursor.execute (*buildInsertStatement ("INSERT %s SET" % APPLICATIONS_TABLE, self._getParams ()))
#			# self.id needs to be updated here
#			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % APPLICATIONS_TABLE, self._getParams ()))
#			reslast = cursor.fetchall ()
#			if len (reslast) == 0:
#				raise DBSelectFaild ('Failed to select previously inserted row. Application-Name: %s' % self.name)
#			#self.id = reslast[-1][0]
#			self.id = reslast[0][0] # hm, the order seems to be the other way around
#		else:
#			# update existing entry
#			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % APPLICATIONS_TABLE, self._getParams (), {'swID':self.id}))
#		cursor.close ()

class Lessontime (object):
	#ROWS = ['lessonID', 'name', 'description', 'startTime', 'endTime']

	def __init__ (self):
		self.id = None
		self.name = None
		self.description = None
		self.startTime = None
		self.endTime = None

	def reload (self):
		if not self.id:
			raise ValueError ('Id must be set.')
		lt = Lessontime.get (self.id)
		if not lt:
			raise ValueError ('Unable to find Lessontime with id: %d' % self.id)
		self.name = lt.name
		self.description = lt.description
		self.startTime = lt.startTime
		self.endTime = lt.endTime

	@Property
	def swID ():
		def fget (self):
			return self.id
		def fset (self, _id):
			self.id = _id
		return locals ()

	@classmethod
	def get (cls, _id):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE lessonID=%%s" % LESSONTIME_TABLE, (_id, ))
		res = cursor.fetchone ()
		if res:
			lt = Lessontime ()
			lt.id = res[0]
			lt.name = res[1]
			lt.description = res[2]
			lt.startTime = res[3]
			lt.endTime = res[4]
			cursor.close ()
			return lt
		cursor.close ()

	def delete (self):
		"""
		Deletes Lessontime from DB
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			cursor = CONNECTION.cursor ()

			cursor.execute ("DELETE FROM %s WHERE lessonID=%%s" % LESSONTIME_TABLE, (self.id, ))
			cursor.close ()
			self.id = None

	def _getParams (self):
		return {'name':self.name,
				'description':self.description,
				'startTime':self.startTime,
				'endTime':self.endTime}

	def save (self):
		"""
		Saves Lessontime to DB
		"""
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		if self.id == None:
			# insert new entry
			cursor.execute (*buildInsertStatement ("INSERT %s SET" % LESSONTIME_TABLE, self._getParams ()))
			# self.id needs to be updated here
			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % LESSONTIME_TABLE, self._getParams ()))
			reslast = cursor.fetchall ()
			if len (reslast) == 0:
				raise DBSelectFaild ('Failed to select previously inserted row. Lessontime-Name: %s' % self.name)
			#self.id = reslast[-1][0]
			self.id = reslast[0][0] # hm, the order seems to be the other way around
		else:
			# update existing entry
			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % LESSONTIME_TABLE, self._getParams (), {'lessonID':self.id}))
		cursor.close ()

##### Convenience functions
def getReservationsList(getReplacedBy=False):
	if not CONNECTION:
		raise ConnectionNotAvailable ()
	cursor = CONNECTION.cursor()
	if getReplacedBy:
		cursor.execute("SELECT reservationID, startTime FROM %s ORDER BY startTime" % RESERVATION_TABLE)
	else:
		cursor.execute("SELECT reservationID, replacedByID, startTime FROM %s WHERE replacedByID IS NULL ORDER BY startTime" % RESERVATION_TABLE)
	res_list = cursor.fetchall()
	cursor.close ()

	# return a list of Reservation objects
	reservations = [ Reservation.get( res[0] ) for res in res_list ]
	return reservations

def getProfilesList():
	if not CONNECTION:
		raise ConnectionNotAvailable ()
	cursor = CONNECTION.cursor()
	cursor.execute("SELECT resprofileID, isglobaldefault, owner, name FROM %s ORDER BY isglobaldefault DESC, owner, name" % PROFILE_TABLE)
	res_list = cursor.fetchall()
	cursor.close ()

	# return a list of Profile objects
	profiles = [ Profile.get( res[0] ) for res in res_list ]
	return profiles

def getSettingsDict(filter=None):
	if not CONNECTION:
		raise ConnectionNotAvailable ()
	cursor = CONNECTION.cursor()
	if filter:
		cursor.execute("SELECT ressettingID, type FROM %s WHERE type=%%s" % SETTINGS_TABLE, (filter,) )
	else:
		cursor.execute("SELECT ressettingID FROM %s" % SETTINGS_TABLE)
	res_list = cursor.fetchall()
	cursor.close ()

	# return a dict of Settings
	settingsDict = {}
	for res in res_list:
		s = Setting.get( res[0] )
		settingsDict[ s.name ] = s
	return settingsDict

def getApplicationsDict(imageActive=False):
	if not CONNECTION:
		raise ConnectionNotAvailable ()
	cursor = CONNECTION.cursor()
	cursor.execute("SELECT swID, imageActive FROM %s WHERE imageActive=%%d" % APPLICATIONS_TABLE, (imageActive, ) )
	res_list = cursor.fetchall()
	cursor.close ()

	# return a dict of software information
	applicationsDict = {}
	for res in res_list:
		applicationsDict = [ Application.get( res[0] ) for res in res_list ]
	return applicationsDict

def getLessontimesList():
	if not CONNECTION:
		raise ConnectionNotAvailable ()
	cursor = CONNECTION.cursor()
	cursor.execute("SELECT lessonID, name, description, startTime, endTime FROM %s ORDER BY startTime" % LESSONTIME_TABLE)
	res_list = cursor.fetchall()
	cursor.close ()

	# return a list of Lessontime objects
	lessontimes = [ Lessontime.get( res[0] ) for res in res_list ]
	return lessontimes

class Vacation (object):
	def __init__ (self):
		self.id = None
		self.name = None
		self.description = None
		self.startDate = None
		self.endDate = None

	def reload (self):
		if not self.id:
			raise ValueError ('Id must be set.')
		v = Vacation.get (self.id)
		if not v:
			raise ValueError ('Unable to find Vacation with id: %d' % self.id)
		self.name = v.name
		self.description = v.description
		self.startDate = v.startDate
		self.endDate = v.endDate

	@Property
	def vacationID ():
		def fget (self):
			return self.id
		def fset (self, _id):
			self.id = _id
		return locals ()

	@classmethod
	def get (self, _id):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE vacationID=%%s" % VACATION_TABLE, (_id, ))
		res = cursor.fetchone ()
		if res:
			v = Vacation ()
			v.id = res[0]
			v.name = res[1]
			v.description = res[2]
			v.startDate = res[3]
			v.endDate = res[4]
			cursor.close ()
			return v
		cursor.close ()

	@classmethod
	def getByDate (self, date):
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		cursor.execute ("SELECT * FROM %s WHERE startDate <= %%s AND endDate >= %%s" % VACATION_TABLE, (date, date))
		vacations = []
		for res in cursor.fetchall ():
			v = Vacation ()
			v.id = res[0]
			v.name = res[1]
			v.description = res[2]
			v.startDate = res[3]
			v.endDate = res[4]
			vacations.append (v)
		cursor.close ()
		return vacations

	def delete (self):
		"""
		Delete Vacation from DB
		"""
		if self.id != None:
			if not CONNECTION:
				raise ConnectionNotAvailable ()
			cursor = CONNECTION.cursor ()
			# delete vacation
			cursor.execute ("DELETE FROM %s WHERE vacationID=%%s" % VACATION_TABLE, (self.id, ))
			cursor.close ()
			self.id = None

	def _getParams (self):
		return {'name':self.name,
				'description':self.description,
				'startDate':self.startDate,
				'endDate':self.endDate}

	def save (self):
		"""
		Saves Vacation to DB
		"""
		if not CONNECTION:
			raise ConnectionNotAvailable ()
		cursor = CONNECTION.cursor ()
		if self.id == None:
			# insert new entry
			cursor.execute (*buildInsertStatement ("INSERT %s SET" % VACATION_TABLE, self._getParams ()))
			# self.id needs to be updated here
			cursor.execute (*buildSelectStatement ("SELECT * FROM %s WHERE" % VACATION_TABLE, self._getParams ()))
			reslast = cursor.fetchall ()
			if len (reslast) == 0:
				raise DBSelectFaild ('Failed to select previously inserted row. Vacation-Name: %s' % self.name)
			#self.id = reslast[-1][0]
			self.id = reslast[0][0] # hm, the order seems to be the other way around
		else:
			# update existing entry
			cursor.execute (*buildUpdateStatement ("UPDATE %s SET" % VACATION_TABLE, self._getParams (), {'vacationID':self.id}))
		cursor.close ()

class Lesson (object):
	def __init__ (self):
		raise NotImplementedError ("Lessons are not yet implemented ")

##### Test to verify that all DB-Objects work expectedly
def test ():
	import datetime
	r = Reservation ()
	r.name = 'reservation'
	r.description = 'description'
	r.owner = 1
	r.hostgroup = 2
	r.usergroup = 3
	r.startTime = datetime.datetime (2000, 01, 01, 12, 0, 0)
	r.endTime = datetime.datetime (2001, 01, 01, 13, 0, 0)
	r.iterationDays = 1
	r.iterationEnd = datetime.datetime (2001, 01, 01, 0, 0, 0)
	r.iterateInVacations = False
	r.save ()
	assert r.id != None
	assert r.id == r.reservationID

	r_new = Reservation.get (r.id)
	assert r_new.reservationID == r_new.id
	assert r_new.id == r.id
	assert r_new.name == r.name
	assert r_new.description == r.description
	assert r_new.owner == r.owner
	assert r_new.hostgroup == r.hostgroup
	assert r_new.usergroup == r.usergroup
	assert r_new.startTime == r.startTime
	assert r_new.endTime == r.endTime
	assert r_new.iterationDays == r.iterationDays
	assert r_new.iterationEnd == r.iterationEnd
	assert r_new.iterateInVacations == r.iterateInVacations
	assert r_new.resprofileID == r.resprofileID
	assert r_new.status == r.status
	assert r_new.replacedByID == r.replacedByID

	p = Profile ()
	p.name = 'profile'
	p.description = 'description'
	p.owner = 4
	p.isglobaldefault = True
	p.save ()
	assert p.id != None
	assert p.id == p.resprofileID

	p_new = Profile.get (p.id)
	assert p_new.id              == p.id
	assert p_new.resprofileID    == p_new.id
	assert p_new.name            == p.name
	assert p_new.description     == p.description
	assert p_new.owner           == p.owner
	assert p_new.isglobaldefault == p.isglobaldefault

	r.profile = p
	r.save ()
	r.reload ()
	assert r.profile.id == p.id

	s = Setting ()
	s.name = 's1'
	s.shortdescription = 'shortdescription'
	s.description = 'description'
	s.type = 'reservation'
	s.ucrStart = 'set test/setting=yes'
	s.ucrStop = 'unset test/setting'
	s.cmdStart = 'echo test'
	s.cmdStop = 'echo test2'
	s.save ()
	assert s.id != None
	assert s.id == s.ressettingID

	s_new = Setting.get (s.id)
	assert s_new.id               == s.id
	assert s_new.id               == s_new.ressettingID
	assert s_new.name             == s.name
	assert s_new.shortdescription == s.shortdescription
	assert s_new.description      == s.description
	assert s_new.type             == s.type
	assert s_new.ucrStart         == s.ucrStart
	assert s_new.ucrStop          == s.ucrStop
	assert s_new.cmdStart         == s.cmdStart
	assert s_new.cmdStop          == s.cmdStop

	o = Option (r)
	o.setting = s
	o.value = 'value'
	o.save ()
	assert o.id != None

	o_new = Option.get (o.id, o.relative)
	assert o_new.id               == o.id
	assert o_new.relative.id      == o.relative.id
	assert o_new.setting.id       == o.setting.id
	assert o_new.value            == o.value

	r.reload ()
	assert len (r.options) == 1
	assert r.options[0].id == o.id
	assert r.options[0].setting.id == o.setting.id

	s2 = Setting ()
	s2.name = 's2'
	s2.type = 'profile'
	s2.save ()
	assert s2.id != None

	o2 = Option (p)
	o2.setting = s2
	o2.save ()
	assert o2.id != None

	v = Vacation ()
	v.name = 'vacation'
	v.description = 'description'
	t = datetime.datetime.now ()
	v.startDate = datetime.datetime.fromordinal (t.toordinal ())
	v.endDate = datetime.datetime.fromordinal (t.toordinal () + 10)
	v.save ()
	assert v.id != None
	assert v.id == v.vacationID

	v_new = Vacation.get (v.id)
	assert v_new.id               == v.id
	assert v_new.id               == v_new.vacationID
	assert v_new.name             == v.name
	assert v_new.description      == v.description
	assert v_new.startDate        == v.startDate
	assert v_new.endDate          == v.endDate

	p.reload ()
	assert len (p.options) == 1
	assert p.options[0].id == o2.id
	assert p.options[0].setting.id == s2.id

	try:
		o2.setting = s
		o2.save ()
		assert False
	except IllegalRelation:
		pass

	try:
		o.setting = s2
		o.save ()
		assert False
	except IllegalRelation:
		pass

	try:
		Option (r).save ()
	except InsufficientRelations:
		pass

	try:
		Option (p).save ()
	except InsufficientRelations:
		pass

	r.delete ()
	assert r.id == None
	p.delete ()
	assert p.id == None
	s.delete ()
	assert s.id == None
	s2.delete ()
	assert s2.id == None
	v.delete ()
	assert v.id == None

	try:
		o.reload ()
		assert False
	except ValueError:
		pass

	try:
		o2.reload ()
		assert False
	except ValueError:
		pass

	try:
		p.reload ()
		assert False
	except ValueError:
		pass

	try:
		r.reload ()
		assert False
	except ValueError:
		pass

	try:
		s.reload ()
		assert False
	except ValueError:
		pass

if __name__ == '__main__':
	host   = 'localhost'
	user   = 'root'
	passwd = ''
	db     = 'reservation'
	connect (host=host, user=user, passwd=passwd, db=db)

	test ()
