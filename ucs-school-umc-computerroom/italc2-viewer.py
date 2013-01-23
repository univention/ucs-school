#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Control computers of pupils in a room
#
# Copyright 2012-2013 Univention GmbH
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

import inspect
import os
import sys
import notifier
import optparse

script_dir = os.path.abspath( os.path.dirname( inspect.getfile(inspect.currentframe() ) ) )
sys.path.insert( 0, os.path.join( script_dir, 'umc/python/computerroom' ) )

import italc2
import ucsschool.lib.schoolldap as usl

import univention.config_registry as ucr

from PyQt4 import QtCore, QtGui

class ViewerApp( QtGui.QApplication ):
	def recvQuit( self, mmsg, data = None ):
		self.quit()

class ImageViewer(QtGui.QMainWindow):
	def __init__( self, options ):
		super(ImageViewer, self).__init__()

		self.printer = QtGui.QPrinter()
		self.scaleFactor = 0.0

		self.imageLabel = QtGui.QLabel()
		self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
		self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored,
				QtGui.QSizePolicy.Ignored)
		self.imageLabel.setScaledContents(True)

		self.scrollArea = QtGui.QScrollArea()
		self.scrollArea.setBackgroundRole(QtGui.QPalette.Dark)
		self.scrollArea.setWidget(self.imageLabel)
		self.setCentralWidget(self.scrollArea)
		self.scrollArea.setWidgetResizable( True )

		self.setWindowTitle("Image Viewer")
		self.resize(500, 400)

		self.italcManager = italc2.ITALC_Manager( options.username, options.password )
		self.italcManager.school = options.school
		self.italcManager.room = options.room
		self.computer = self.italcManager[ options.computer ]
		self._timer = notifier.timer_add( 500, self.updateScreenshot )

	def updateScreenshot( self, dummy ):
		if not self.computer.screenshotQImage.isNull():
			self.open( image = self.computer.screenshotQImage )
		return True

	def open( self, fileName = None, image = None ):
		if fileName:
			image = QtGui.QImage(fileName)
		if image.isNull():
			QtGui.QMessageBox.information(self, "Image Viewer",
					"Cannot load %s." % fileName)
			return

		self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(image))
		self.scaleFactor = 1.0
		self.resize( image.width(), image.height() )

	def scaleImage(self, factor):
		self.scaleFactor *= factor
		self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

		self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
		self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

		self.zoomInAct.setEnabled(self.scaleFactor < 3.0)
		self.zoomOutAct.setEnabled(self.scaleFactor > 0.333)

	def adjustScrollBar(self, scrollBar, factor):
		scrollBar.setValue(int(factor * scrollBar.value()
								+ ((factor - 1) * scrollBar.pageStep()/2)))


if __name__ == '__main__':
	global imageviewer
	config = ucr.ConfigRegistry()
	config.load()

	notifier.init( notifier.QT )

	parser = optparse.OptionParser()
	parser.add_option( '-s', '--school', dest = 'school', default = '711' )
	parser.add_option( '-r', '--room', dest = 'room', default = 'room01' )
	parser.add_option( '-c', '--computer', dest = 'computer', default = 'WIN7PRO' )
	parser.add_option( '-u', '--username', dest = 'username', default = 'Administrator' )
	parser.add_option( '-p', '--password', dest = 'password', default = 'univention' )
	options, args = parser.parse_args()

	usl.set_credentials( 'uid=%s,cn=users,%s' % ( options.username, config.get( 'ldap/base' ) ), options.password )

	app = ViewerApp( sys.argv )
	print app.quitOnLastWindowClosed()
	app.lastWindowClosed.connect( app.quit, QtCore.Qt.DirectConnection )
	imageViewer = ImageViewer( options )
	imageViewer.show()

	notifier.loop()

	print 'finished'
