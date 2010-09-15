#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: printer moderation module
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
import univention.management.console.protocol as umcp

import univention.debug as ud

_ = umc.Translation( 'univention.management.console.handlers.printermoderation' ).translate

BACKBUTTON = lambda ou, group: umcd.Button (_ ('Back'), 'printermoderation/back', \
		actions=[umcd.Action ( umcp.Command (args=['printermoderation/list'], \
		opts = {'ou':ou, 'selectedgroup':group}))])

import inspect
def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo = []
	if len(info[0])>28:
		printInfo.append('...'+info[0][-25:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))

class Web( object ):
	def _generate_printjoblist_header (self):
		header = [ '', _( 'Username' ), _( 'Full Name' ), _( 'Printjob Name' ), _( 'Creation Time' ) ]
		header.append (_ ('Operations'))
		return header

	def _generate_printjoblist_operations (self, printjob, checkbox, additional_static_options):
		operations = umcd.List ()
		line = []

		myoptions = additional_static_options.copy()
		myoptions['jobs'] = [(printjob.owner.dn, printjob.filename)]

		r_req = umcp.Command (args = [ 'printermoderation/job/review' ], opts = myoptions)
		_review = umcd.Action (r_req)
		p_req = umcp.Command (args = [ 'printermoderation/job/print' ], opts = myoptions)
		_print = umcd.Action (p_req)
		d_req = umcp.Command (args = [ 'printermoderation/job/delete' ], opts = myoptions)
		_delete = umcd.Action (d_req)

		b_review = umcd.Button (_ ('Review'), 'printermoderation/review', _review)
		line.append (b_review)
		b_print = umcd.Button (_ ('Print'), 'printermoderation/print', _print)
		line.append (b_print)
		b_delete = umcd.Button (_ ('Delete'), 'printermoderation/delete', _delete)
		line.append (b_delete)

		if checkbox:
			line.append( checkbox )

		operations.add_row (line)
		return operations

	def _generate_printjoblist_element (self, printjob, checkbox, additional_static_options):
		icon = "printermoderation/pdf"
		element = [umcd.Image( icon ),
				printjob.owner.info['username'],
				'%s %s' % (printjob.owner.info['firstname'], printjob.owner.info['lastname']),
				printjob.name,
				umcd.Date (printjob.ctime.strftime ('%d.%m.%y %H:%M'))]
		element.append (self._generate_printjoblist_operations (printjob, checkbox, additional_static_options))
		return element

	def _generate_printjoblist_table (self, printjoblist, additional_static_options):
		tablelst = umcd.List()
		tablelst.set_header (self._generate_printjoblist_header ())
		boxes = []

		for printjob in printjoblist: # got Printjob here
			myoptions = additional_static_options.copy()
			myoptions['jobs'] = (printjob.owner.dn, printjob.filename)
			chk = umcd.Checkbox( static_options = myoptions )
			boxes.append( chk.id() )
			tablelst.add_row( self._generate_printjoblist_element( printjob, chk, additional_static_options ) )

		return (tablelst, boxes)

	def _generate_printjoblist_select(self, boxes, choices, req_opts):
		myopts = req_opts.copy()
		myopts['jobs'] = []
		req = umcp.Command( opts = myopts )
		#req.set_flag( 'web:startup', True )
# 		req.set_flag( 'web:startup_reload', True )
		#req.set_flag( 'web:startup_format', _( 'reset passwords' ) )
		actions = ( umcd.Action( req, boxes, True ) )
		return umcd.SelectionButton( _( ' Select the Operation' ), choices, actions )

	def _generate_printer_selection (self, printers, req_opts):
		plst = umcd.List ()

		if len (printers) > 0:
			plst.add_row ([_ ('Select a printer')])
			for p in printers:
				myoptions = req_opts.copy()
				myoptions['selectedprinter'] = p.dn
				print myoptions
				action = umcd.Action (umcp.Command (args=['printermoderation/job/print'], opts=myoptions))
				plst.add_row ([umcd.Button (p.info['name'], 'printermoderation/print', [action])])
		else:
			plst.add_row ([_ ('No printers available') ])

		return plst

	def _web_printermoderation_list (self, umcobject, res):
		availableOU, grouplist, selectedgroup, printjoblist, messages = res.dialog
		currentOU = umcobject.options.get( 'ou', availableOU[0] )

		ud.debug( ud.ADMIN, ud.INFO, '_web_printermoderation_list: options: %s' % str( umcobject.options ) )
		ud.debug( ud.ADMIN, ud.INFO, '_web_printermoderation_list: dialog: %s' % str( res.dialog ) )

		headline = _( "Printer Moderation" )

		lst = umcd.List()

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		if len(availableOU) > 1:
			ouchoices = []
			defaultchoice = 0
			for ou in availableOU:
				if ou == currentOU:
					defaultchoice = len(ouchoices)
				ouchoices.append( { 'description' : ou,
									'actions': [ umcd.Action( umcp.Command( args = ['printermoderation/list'],
																			opts = { 'ou' : ou } ) ) ] } )

			ouselect = umcd.ChoiceButton( _('Please select department:'), ouchoices, default = defaultchoice )
			ouselect['width'] = '300'
			lst.add_row( [ ouselect ] )

		groupchoices = []
		defaultchoice = 0
		for group in grouplist:
			if group == selectedgroup:
				defaultchoice = len(groupchoices)
			groupchoices.append( { 'description' : group,
					       'actions': [ umcd.Action( umcp.Command( args = ['printermoderation/list'],
										       opts = { 'selectedgroup' : group, 'ou': currentOU } ) ) ] } )

		groupselect = umcd.ChoiceButton( _('Select Class'), groupchoices, default = defaultchoice )
		groupselect['width'] = '300'
		lst.add_row( [ groupselect ] )

		# stop if no group is selected
		if not selectedgroup or selectedgroup == _( 'No group selected' ):
			res.dialog = umcd.Frame( [ lst ], headline )
			self.revamped( umcobject.id(), res )
			return

		# create user table
		# TODO sort printjob list by creation time
		tablelst, boxes = self._generate_printjoblist_table (printjoblist, \
				additional_static_options = \
				{ 'selectedgroup' : selectedgroup, 'ou': currentOU })
				# don't change the selected group

		# create operations selectbox
		refresh = umcd.Button (_ ('Refresh'), \
				'printermoderation/refresh',
				[umcd.Action( \
				umcp.Command( args = ['printermoderation/list'], \
				opts = { 'selectedgroup' : selectedgroup, 'ou': currentOU }))])
		select = self._generate_printjoblist_select( boxes, \
				[ ('printermoderation/job/print', _ ('Print Selected Items')), \
				('printermoderation/job/delete', _( 'Delete Selected Items' )) ], \
				req_opts = {'selectedgroup' : selectedgroup, 'ou': currentOU })
		tablelst.add_row ([umcd.Fill (4), refresh, select])

		lst.add_row( [ tablelst ] )

		res.dialog = umcd.Frame( [ lst ], headline )
		self.revamped( umcobject.id(), res )

	def _web_printermoderation_job_delete (self, umcobject, res):
		currentOU, selectedgroup, deletedjobs, messages = res.dialog
		lst = umcd.List()

		headline = _( "Deleted Print Jobs" )

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		table = umcd.List()
		table.set_header (self._generate_printjoblist_header ()[:-1])
		for printjob in deletedjobs:
			table.add_row ([umcd.Image ('printermoderation/delete'),
					printjob.owner.info['username'], \
					'%s %s' % (printjob.owner.info['firstname'], printjob.owner.info['lastname']), \
					printjob.name,
					umcd.Date (printjob.ctime.strftime ('%d.%m.%y %H:%M'))])

		lst.add_row ([table])

		lst.add_row ([BACKBUTTON (currentOU, selectedgroup)])

		res.dialog = umcd.Frame([lst], headline)
		self.revamped (umcobject.id(), res)

	def _web_printermoderation_job_print (self, umcobject, res):
		currentOU, selectedgroup, printers, selectedprinter, jobs, \
				printedjobs, messages = res.dialog
		lst = umcd.List()

		headline = _( "Printed Jobs" )

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		if not selectedprinter:
			lst.add_row ([self._generate_printer_selection (printers, \
					{'ou':currentOU, 'selectedgroup':selectedgroup, 'jobs':jobs})])
		else:
			table = umcd.List()
			table.set_header (self._generate_printjoblist_header ()[:-1])
			for printjob in printedjobs:
				table.add_row ([umcd.Image ('printermoderation/printok'),
						printjob.owner.info['username'], \
						'%s %s' % (printjob.owner.info['firstname'], printjob.owner.info['lastname']), \
						printjob.name,
						umcd.Date (printjob.ctime.strftime ('%d.%m.%y %H:%M'))])

			lst.add_row ([table])

		lst.add_row ([BACKBUTTON (currentOU, selectedgroup)])

		res.dialog = umcd.Frame([lst], headline)
		self.revamped (umcobject.id(), res)

	def _web_printermoderation_job_review (self, umcobject, res):
		currentOU, selectedgroup, printjob, messages = res.dialog
		lst = umcd.List()

		headline = _( "Review Printjob" )

		# add messages if any
		if messages:
			for message in messages:
				lst.add_row( [ message ] )

		if printjob:
			llst = umcd.List ()
			_review = umcd.Link (_ ('Review Printjob') + (' %s' % printjob.name), \
					'/univention-management-console/filedownload.php?filename=%s' \
					% printjob.getRelativeTmpfilename (), 'printermoderation/pdf')
			llst.add_row ([_review, ' %s' % printjob.name])
			lst.add_row ([llst])

		lst.add_row ([BACKBUTTON (currentOU, selectedgroup)])

		res.dialog = umcd.Frame([lst], headline)
		self.revamped (umcobject.id(), res)
