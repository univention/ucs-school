# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Base class for output writers.
"""
# Copyright 2016 Univention GmbH
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


class BaseWriter(object):
	"""
	Abstraction of a data dump mechanism like CSV, JSON, XML, sockets etc.
	"""

	def __init__(self, *arg, **kwargs):
		"""
		Create a writer.

		:param arg: list
		:param kwargs: dict
		"""

	def open(self, filename, mode="wb"):
		"""
		Get a handle on the output file or something similar to be used as a
		context manager.
		IMPLEMENTME with the method appropriate for the output type.

		:param filename: str: filename to write data to
		:param mode: str: passed to used open() method
		:return: a context manager
		"""
		raise NotImplementedError()

	def write_header(self, header):
		"""
		Write an optional header (line) before the main data.
		IMPLEMENTME if you wish to write a header line.

		:param header: object to write as header
		:return: None
		"""

	def write_footer(self, footer):
		"""
		Write a optional footer (line) after the main data.
		IMPLEMENTME if you wish to write a footer.

		:param footer: object to write as footer
		:return: None
		"""

	def write_obj(self, obj):
		"""
		Write object to output.
		IMPLEMENTME if it's not just outfile.write(obj).

		:param obj: object or error to write
		:return: result of write operation, if any
		"""
		raise NotImplementedError()
