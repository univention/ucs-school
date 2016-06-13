# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Base class for result exporters.
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


class ResultExporter(object):
	"""
	Write a CSV/JSON/XML file representing the result of an import job.
	Create one writer per object type.

	Clients of this class should only call dump().

	Subclasses implement get_iter() to create a stream of objects to serialize
	and run serialize() on each of them.
	"""
	def __init__(self, *arg, **kwargs):
		"""
		Create a CSV file writer.

		:param arg: list
		:param kwargs: dict
		"""
		pass

	def dump(self, import_handler, filename):
		"""
		Create file about added/modified/deleted objects and errors.

		:param import_handler: object that contains data to dump from an
		import job (for example UserImport)
		:param filename: str: filename to write data to
		"""
		writer = self.get_writer()
		with writer.open(filename):
			writer.write_header(self.get_header())
			for obj in self.get_iter(import_handler):
				row = self.serialize(obj)
				writer.write_obj(row)
			writer.write_footer(self.get_footer())

	def get_footer(self):
		"""
		Data for an optional footer (line) after the main data.
		IMPLEMENTME if you wish to write a footer.

		:return: object that can be used by the writer to create a footer
		"""
		pass

	def get_header(self):
		"""
		Data for an optional header (line) before the main data.
		IMPLEMENTME if you wish to write a header line.

		:return: object that can be used by the writer to create a header
		"""
		pass

	def get_iter(self, import_handler):
		"""
		Iterator over all created objects and errors of an import job.
		IMPLEMENTME to change the order of objects and errors in the generated
		output.

		:param import_handler: object that contains data to dump from an
		import job
		:return: iterator: both import objects and UcsSchoolImportError objects
		"""
		raise NotImplementedError()

	def get_writer(self):
		"""
		Object that will write the data to disk/network in the desired format.
		IMPLEMENTME

		:return: an object that knows how to write data
		"""
		raise NotImplementedError()

	def serialize(self, obj):
		"""
		Make a dict of attr_name->strings from an import object.
		IMPLEMENTME to dump a single object (user/computer/error) delivered by
		the iterator from get_iter().

		:param obj: object to serialize
		:return: dict: attr_name->strings that will be used to write the
		output file
		"""
		raise NotImplementedError()
