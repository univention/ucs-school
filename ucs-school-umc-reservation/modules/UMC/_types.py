#!/usr/bin/python2.4
#
# Univention Management Console
#  module: Reservation
#
# Copyright 2007-2010 Univention GmbH
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

import univention.management.console as umc
import univention.management.console.dialog as umcd
import univention.debug as ud
import univention.uldap
import time
import datetime
import operator
import pwd
import univention.reservation.dbconnector as reservationdb

_ = umc.Translation( 'univention.management.console.handlers.reservation' ).translate

label_please_choose_and_add='--- %s ---' % _('Please choose and add')

AdminUser = 'root'
AdminUserUID = pwd.getpwnam(AdminUser)[2]

class Reservation_SearchKeys( umc.StaticSelection ):
	def __init__( self, label, required = True ):
		umc.StaticSelection.__init__( self, label, required = required )

	def choices( self ):
		return ( ( 'roomname', _( 'Room' ) ), ( 'groupname', _( 'Group' ) ), ( 'ownername', _( 'Owner' ) ) )

umcd.copy( umc.StaticSelection, Reservation_SearchKeys )

class Profile_SearchKeys( umc.StaticSelection ):
	def __init__( self, label, required = True ):
		umc.StaticSelection.__init__( self, label, required = required )

	def choices( self ):
		return ( ( 'profile_name', _( 'Profile Name' ) ), ( 'description', _( 'Description' ) ) )

umcd.copy( umc.StaticSelection, Profile_SearchKeys )

baseDatetime = datetime.datetime( *time.strptime('0','%S')[0:3]) # base datetime object to convert timedelta objects..
class TimeTable(object):
	data = []
	def __init__(self):
		pass

	def update(self):
		lessontimes = reservationdb.getLessontimesList()
		newdata = []
		for lt in lessontimes:
			startTimeObj = (baseDatetime + lt.startTime).time()
			endTimeObj = (baseDatetime + lt.endTime).time()
			# timetable format: (datetime.time, datetime.time, string)
			newdata.append([ startTimeObj, endTimeObj, lt.name ])
		self.data = sorted( newdata, key = operator.itemgetter(0) )

timetable = TimeTable()

def time_to_lesson(time_str): 
	time_obj = datetime.time(* time.strptime(time_str, "%H:%M")[3:6])
	for start_obj, end_obj, name in timetable.data:
		#start_obj = time.strptime(start, "%H:%M")
		if time_obj >=  start_obj:
			#end_obj = time.strptime(end, "%H:%M")
			if time_obj <= end_obj:
				return {'start': start_obj.strftime("%H:%M"), 'end': end_obj.strftime("%H:%M"), 'name': name}
	return {'start': '', 'end': '', 'name': ''}

def endtime_to_lesson(time_str): 
	time_obj = datetime.time(* time.strptime(time_str, "%H:%M")[3:6])
	for start_obj, end_obj, name in timetable.data:
		#end_obj = time.strptime(end, "%H:%M")
		if time_obj <= end_obj:
			return {'start': start_obj.strftime("%H:%M"), 'end': end_obj.strftime("%H:%M"), 'name': name}
	return {'start': '', 'end': '', 'name': ''}

class SyntaxTimeStart( umc.StaticSelection ):
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )

	def set_today( self, today=True ):
		self.today = today
		self._choices = self._recalculate_choices()

	def choices( self ):
		return self._choices

	def _recalculate_choices( self ):
		_choices = []
		for start_obj, end_obj, name in timetable.data:
			start = start_obj.strftime("%H:%M")
			_choices.append( ( start, name + ' (' + start + ')' ) )
		if self.today:
			_choices.insert(0, ( 'now', _('Now') ) )
		return _choices

umcd.copy( umc.StaticSelection, SyntaxTimeStart )


class SyntaxTimeEnd( umc.StaticSelection ):
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )
		self._choices = []

	def set_time_begin( self, time_begin ):
		self.time_begin = time_begin
		self._choices = self._recalculate_choices()

	def choices( self ):
		return self._choices

	def _recalculate_choices( self ):
		_choices = []
		# parse time string to a datetime.time object
		if self.time_begin == 'now':
			#time_obj = datetime.time(* time.localtime()[3:6])
			time_obj = datetime.datetime.now().time()
		else:
			time_obj = datetime.time(* time.strptime(self.time_begin, "%H:%M")[3:6])
		for start_obj, end_obj, name in timetable.data:
			if start_obj >= time_obj:
				end = end_obj.strftime("%H:%M")
				_choices.append( ( end, name + ' (' + end + ')' ) )
		if _choices:
			_choices.insert(0, ( 'endoflesson', _('End of Lesson') ) )
		else:
			_choices = [ ( 'in45min', _('In 45 min.') ),
			             ( 'in1.5h', _('In 1.5 hours') ),
			             ( 'in3h', _('In 3 hours') ),
			             ( 'endofday', _('End of day') )
				   ]
		return _choices

umcd.copy( umc.StaticSelection, SyntaxTimeEnd )

class SyntaxIterationRhythm( umc.StaticSelection ):
	_choices = [ ('0', _('None') ),
		     ('1', _('Daily') ),
		     ('2', _('Every 2nd Day') ),
		     ('3', _('Every 3rd Day') ),
		     ('4', _('Every 4th Day') ),
		     ('5', _('Every 5th Day') ),
		     ('6', _('Every 6th Day') ),
		     ('7', _('Weekly') ),
		     ('14', _('Biweekly') ),
		   ]
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		return self._choices

umcd.copy( umc.StaticSelection, SyntaxIterationRhythm )

class SyntaxHoliday( umc.StaticSelection ):
	_choices = []
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )
		self._choices.append( ( '::notset', _('No Exception') ) )
		self._choices.append( ( '08Feiertage', _('Public Holidays')+' 2008' ) )
		self._choices.append( ( '08Herbstferien', _('Autumn Holidays')+' 2008' ) )
		self._choices.append( ( '08Weihnachtsferien', _('Christmas Holidays')+' 2008' ) )

	def choices( self ):
		return self._choices

umcd.copy( umc.StaticSelection, SyntaxHoliday )

class SyntaxSchoolterm( umc.StaticSelection ):
	_choices = []
	def __init__( self, name, required = True, choices = [] ):
		umc.StaticSelection.__init__( self, name, required = required )
		self._choices.append( ( '::notset', _('No Term') ) )
		self._choices.append( ( '08HalbjahrWinter', _('Winter Term')+' 2008' ) )
		self._choices.append( ( '09HalbjahrSommer', _('Summer Term')+' 2009' ) )
		self._choices.append( ( '09HalbjahrWinter', _('Winter Term')+' 2009' ) )

	def choices( self ):
		return self._choices

umcd.copy( umc.StaticSelection, SyntaxSchoolterm )

syntax={} ## the syntax container, used to access dynamic choices generated in _revamp

class SyntaxUserGroup( umc.StaticSelection ):
	_choices = []
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		return self._choices

umcd.copy( umc.StaticSelection, SyntaxUserGroup )

class SyntaxHostGroup( umc.StaticSelection ):
	_choices = []
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		return self._choices

umcd.copy( umc.StaticSelection, SyntaxHostGroup )

class SyntaxProfile( umc.StaticSelection ):
	_choices = []
	def __init__( self, name, required = True ):
		umc.StaticSelection.__init__( self, name, required = required )

	def choices( self ):
		return self._choices

umcd.copy( umc.StaticSelection, SyntaxProfile )

def Property (func):
	return property(doc=func.__doc__, **func())

class ProgramAllowSelection( umc.StaticSelection ):
	def __init__( self, required = True ):
		umc.StaticSelection.__init__( self, _( 'Reserve Program Licenses' ), required = required )

	inactive_applications = None

	def choices( self ):
		# build list of Programs
		if not self.inactive_applications:
			self.inactive_applications = reservationdb.getApplicationsDict(imageActive=False)
		lst = [ ('pleaseselect', label_please_choose_and_add) ]
		lst.extend( [ [ self.inactive_applications[appname].id, appname ] for appname in self.inactive_applications ] )
		return lst

umcd.copy( umc.StaticSelection, ProgramAllowSelection )

# class ProgramLicenseSelection( umc.StaticSelection ):
#         def __init__( self, required = True ):
#                 umc.StaticSelection.__init__( self, _( 'Licenses' ), required = required )
# 		for entry in demodata.programs_license:
# 			_licenses[entry[0]] = entry[2]
# 
#         _licenses = {}
#         def set_datetimeprogram( self, datetimeiso, progID ):
# 		self.datetimestring = datetimestring
# 		licenses = _licenses[progID]
# 		if progID in calendar[datetimestring].bookedprograms:
# 			licenses -= calendar[datetimestring].bookedprograms[progID]
# 		return licenses
#         def choices( self ):
# 		lst = [ ('pleaseselect', label_please_choose_and_add) ]
#                 # build list of Programs
# 		lst.extend( [ (n, n) for n in range(licenses) ] )
#                 return lst
# 
# umcd.copy( umc.StaticSelection, ProgramLicenseSelection )
# 
class ProgramDenySelection( umc.StaticSelection ):
	def __init__( self, required = True ):
		umc.StaticSelection.__init__( self, _( 'Deny Programs' ), required = required )

	active_applications = None

	def choices( self ):
		if not self.active_applications:
			self.active_applications = reservationdb.getApplicationsDict(imageActive=True)
		lst = [ ('pleaseselect', label_please_choose_and_add) ]
		# build list of Programs
		lst.extend( [ [ self.active_applications[appname].id, appname ] for appname in self.active_applications ] )
		return lst

umcd.copy( umc.StaticSelection, ProgramDenySelection )

# class ProgramAllowSelectionSearch( ProgramAllowSelection ):
#         def __init__( self, required = True ):
#                 ProgramAllowSelection.__init__( self, required )
# 
#         def choices( self ):
#                 lst = ProgramAllowSelection.choices( self )
#                 lst.insert( 0, ( 'all', _( 'All' ) ) )
#                 return lst
# 
# umcd.copy( umc.StaticSelection, ProgramAllowSelectionSearch )
# 
class ProgramAllowSelectionList( umc.String ):
	def __init__( self, required = True ):
		umc.String.__init__( self, _( 'Program Licenses' ), required = required )
		self.label = _( 'List of Program Licenses' )
		self.multivalue = True

umcd.copy( umc.StaticSelection, ProgramAllowSelectionList )

class ProgramDenySelectionList( umc.String ):
	def __init__( self, required = True ):
		umc.String.__init__( self, _( 'Disabled Program'), required = required )
		self.label = _( 'List of Disabled Programs' )
		self.multivalue = True

umcd.copy( umc.StaticSelection, ProgramDenySelectionList )

# class SharemodeSelection( umc.StaticSelection ):
#         def __init__( self, required = True ):
#                 umc.StaticSelection.__init__( self, _( 'Sharemode' ), required = required )
# 
#         def choices( self ):
#                 # build list of Sharemodes
#                 lst = [('noaccess', _('No Access') ), ('normal', _('Normal Access') )]
#                 return lst
# 
# umcd.copy( umc.StaticSelection, SharemodeSelection )
# 
# class ShareSelection( umc.StaticSelection ):
#         def __init__( self, required = True ):
#                 umc.StaticSelection.__init__( self, _( 'Share' ), required = required )
# 
#         def choices( self ):
#                 # build list of Shares
#                 lst = [('klassenshare', _('Class Share') ), ('marktplatz', 'Common Share')]
#                 return lst
# 
# umcd.copy( umc.StaticSelection, ShareSelection )
# 
# class ShareSelectionSearch( ShareSelection ):
#         def __init__( self, required = True ):
#                 ShareSelection.__init__( self, required )
# 
#         def choices( self ):
#                 lst = ShareSelection.choices( self )
#                 lst.insert( 0, ( 'all', _( 'All' ) ) )
#                 return lst
# 
# umcd.copy( umc.StaticSelection, ShareSelectionSearch )
# 
# class ShareSelectionList( ShareSelection ):
#         def __init__( self, required = True ):
#                 ShareSelection.__init__( self, required = required )
#                 self.label = _( 'List of Shares' )
#                 self.multivalue = True
# 
# umcd.copy( umc.StaticSelection, ShareSelectionList )

class ProxyfilterSelection( umc.StaticSelection ):
	def __init__( self, required = True):
		title = _( 'Internet Filter' )
		umc.StaticSelection.__init__( self, title, required = required )

	proxyfilterlist = None

	def choices( self ):
		# build list of Proxyfilters
		if not self.proxyfilterlist:
			self.proxyfilterlist = [('default', _('Default'))]
			# get UCR
			umc.registry.load()
			keylst = umc.registry.keys()
			proxyfilterkeybase='proxy/filter/setting/'
			keylst = [key for key in keylst if key.startswith(proxyfilterkeybase) and key.endswith('/filtertype')]
			for key in keylst:
				#filtertype = umc.registry[key]
				# type: whitelist-block ODER blacklist-pass ODER whitelist-blacklist-pass
				name = key[:key.rfind('/filtertype')].replace(proxyfilterkeybase,'',1)
				self.proxyfilterlist.append((name, name))
		return self.proxyfilterlist

umcd.copy( umc.StaticSelection, ProxyfilterSelection )

class PrintmodeSelection( umc.StaticSelection ):
	def __init__( self, required = True ):
		umc.StaticSelection.__init__( self, _( 'Printmode' ), required = required )

	def choices( self ):
		lst = [('default', _('Default')), ('all', _('All')), ('none', _('None'))]
		return lst

umcd.copy( umc.StaticSelection, PrintmodeSelection )

class Defaults( dict ):
	def get( self, opts, handler_method, key ):
		default = dict.__getitem__(self, handler_method)
		return opts.get(key) or default.get( key )
	def merge( self, options, handler_method ):
		res = {}
		default = dict.__getitem__(self, handler_method)
		# reset 'empty' options to defaults of 'handler_method'
		for k, v in options.items():
			res[ k ] = v or default.get( k )
		# set defaults given for unset options
		for k in default.keys():
			if not k in options:
				res[ k ] = default[ k ]
		return res

defaults = Defaults()

department = umc.String( _( 'Department' ) )
message = umc.Text( _( 'Message' ) )

sfilter = umc.String( '&nbsp;' , required = False )
searchkey_reservation = Reservation_SearchKeys( _( 'Search Key' ) )
searchkey_profile = Profile_SearchKeys( _( 'Search Key' ) )
date = umc.String( _( 'Date' ) )
syntax['time_begin'] = SyntaxTimeStart( _( 'Start time' ) )
syntax['time_end'] = SyntaxTimeEnd( _( 'End time' ) )
syntax['groupname'] = SyntaxUserGroup( _( 'Class/Project group' ) )
syntax['roomname'] = SyntaxHostGroup( _( 'Room' ) )
syntax['resprofileID'] = SyntaxProfile( _( 'Reservation profile' ) )
reservation = umc.String( _( 'Reservation' ) )
collectfiles = umc.Boolean( _( "Collect pupil's files at end of reservation" ) )
classshare = umc.Boolean( _( 'Access to class share' ) )
schoolshare = umc.Boolean( _( 'Access to school share' ) )
homeshare = umc.Boolean( _( 'Access to home share' ) )
extrashares = umc.Boolean( _( 'Access to other shares' ) )
syntax['rhythm'] = SyntaxIterationRhythm( _( 'Rhythm' ) )
filename = umc.String( _( 'Digital Teaching Resource' ) )
fileupload = umc.FileUploader( _( 'Upload Digital Teaching Resources' ), required = False )
licensedprogram_whitelist = ProgramAllowSelection()
freeprogram_blacklist = ProgramDenySelection()
licenses_avail = umc.Integer( _( 'Number of licenses' ) )
#programsearch = ProgramAllowSelectionSearch()
syntax['licensedprogram_whitelist'] = ProgramAllowSelectionList( required = False )
syntax['freeprogram_blacklist'] = ProgramDenySelectionList( required = False )
#sharemode = SharemodeSelection( required = False )
#share = ShareSelection()
#shares = ShareSelectionList( required = False )
internetfilter = ProxyfilterSelection()
printmode = PrintmodeSelection()
#syntax['lessonID'] = SyntaxLessontime( _( 'Lessontime ID' ) )
timeregex = '^[ ]*(20|21|22|23|[01]\d|\d):[0-5]\d[ ]*$'
syntax['lessontime_name'] = umc.String( _( 'Name' ) )
syntax['description'] = umc.String( _( 'Description (optional)' ), required = False )
syntax['startTime'] = umc.String( _( 'Start time' ), regex = timeregex)
syntax['endTime'] = umc.String( _( 'End time' ), regex = timeregex)
# lessontime_table_syntax = dict( [ ( key, syntax[key] ) for key in 'lessontime_name', 'description', 'startTime', 'endTime' ] )
lessontime_table = umc.MultiDictValue( _( 'Lessontime Definitions' ),
	syntax = { 'lessontime_name' : syntax['lessontime_name'],
	           'description' : syntax['description'],
	           'startTime' : syntax['startTime'],
	           'endTime' : syntax['endTime'] }
	)
#lessontimes_table_heading = [ _( 'Name' ), _( 'Description (optional)' ), _('Start Time'), _('End Time') ]
#lessontimes_table_heading = [ syntax.label for syntax in lessontimes_table.syntax ]


class Reservation (object):
	values = {
	   'reservationID': umc.String( _( 'Reservation ID' ) ),
	   'reservation_name': umc.String( _( 'Reservation Name' ) ),
	   'description': umc.String( _( 'Description (optional)' ), required = False ),
	   'date_start': umc.String( _( 'Date' ) ),
	   'time_begin': syntax['time_begin'],
	   'time_end': syntax['time_end'],
	   'roomname': syntax['roomname'],
	   'groupname': syntax['groupname'],
	   'iterationDays': syntax['rhythm'],
	   'iterationEnd': umc.String( _( 'Date' ) ),
	   'resprofileID': syntax['resprofileID'],
	   'ownername': umc.String( _( 'Owner' ) ),
	   'printmode': printmode,
	   'files': fileupload,
	   'collectfiles': collectfiles,
	}
	defaults = {
			'reservationID': '',
			'reservation_name': '',
			'description': '',
			'date_start': '',
			'time_begin': 'now',
			'time_end': 'endoflesson',
			'roomname': '',
			'groupname': '::notset',
			'iterationDays': '0',
			'iterationEnd': '',
			'resprofileID': '',
			'ownername': '',
			'printmode': 'default',
			'files': [],
	   		'collectfiles': False,
		}
	def __init__(self, instanceDefaults):
		self.defaults.update(instanceDefaults)

class Profile (object):
	values = {
	   'resprofileID': syntax['resprofileID'],
	   'profile_name': umc.String( _( 'Profile name' ) ),
	   'description': umc.String( _( 'Description (optional)' ), required = False ),
	   'ownername': umc.String( _( 'Owner' ) ),
	   'homeshare': homeshare,
	   'schoolshare': schoolshare,
	   'classshare': classshare,
	   'extrashares': extrashares,
	   'swID-act-list': syntax['licensedprogram_whitelist'],
	   'swID-deact-list': syntax['freeprogram_blacklist'],
	   'internetfilter': internetfilter,
	}
	defaults ={
			'resprofileID': '',
			'profile_name': '',
			'description': '',
			'ownername': '',
			'homeshare': True,
			'schoolshare': True,
			'classshare': True,
			'extrashares': True,
			'internetfilter': 'default',
			'swID-act-list': '',
			'swID-deact-list': '',
	}
	def __init__(self, instanceDefaults):
		self.defaults.update(instanceDefaults)

class Lessontime (object):
	values = {
	   #'lessonID': syntax['lessonID'],
	   'lessontime_name': syntax['lessontime_name'],
	   'description': syntax['description'],
	   'startTime': syntax['startTime'],
	   'endTime': syntax['endTime'],
	}
	defaults ={
			#'lessonID': '',
			'lessontime_name': '',
			'description': '',
	   		'startTime': '',
	   		'endTime': '',
	}
	def __init__(self, instanceDefaults):
		self.defaults.update(instanceDefaults)

#class ProfileSetting (object):
#	values = {
#	   'ressettingID': syntax['ressettingID'],
#	   'setting_name': umc.String( _( 'Setting Name' ) ),
#	   'shortdescription': umc.String( _( 'Short Description (optional)' ), required = False ),
#	   'description': umc.String( _( 'Description (optional)' ), required = False ),
#	   'type': umc.String( _( 'Type' ) ),
#	   'ucrStart': umc.String( _( 'UCR Start Command' ) ),
#	   'ucrStop': umc.String( _( 'UCR Stop Command' ) ),
#	   'cmdStart': umc.String( _( 'Shell Start Command' ) ),
#	   'cmdStop': umc.String( _( 'Shell Stop Command' ) ),
#	}
#	defaults ={
#			'ressettingID': '',
#			'setting_name': '',
#			'shortdescription': '',
#			'description': '',
#			'type': '',
#			'ucrStart': '',
#			'ucrStop': '',
#			'cmdStart': '',
#			'cmdStop': '',
#	}
#	def __init__(self, instanceDefaults):
#		self.defaults.update(instanceDefaults)

