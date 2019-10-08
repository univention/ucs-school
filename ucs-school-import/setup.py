#!/usr/bin/python2.7
import io
from distutils.core import setup
from email.utils import parseaddr
from debian.changelog import Changelog
from debian.deb822 import Deb822


dch = Changelog(io.open('debian/changelog', 'r', encoding='utf-8'))
dsc = Deb822(io.open('debian/control', 'r', encoding='utf-8'))
realname, email_address = parseaddr(dsc['Maintainer'])

setup(
	packages=[
		'ucsschool.importer',
		'ucsschool.importer.contrib',
		'ucsschool.importer.frontend',
		'ucsschool.importer.legacy',
		'ucsschool.importer.mass_import',
		'ucsschool.importer.models',
		'ucsschool.importer.reader',
		'ucsschool.importer.utils',
		'ucsschool.importer.writer',
	],
	py_modules=[
		'ucsschool.lib.create_ou',
	],
	package_dir={'': 'modules'},
	description='ucs@school import library',

	url='https://www.univention.de/',
	license='GNU Affero General Public License v3',

	name=dch.package,
	version=dch.version.full_version,
	maintainer=realname,
	maintainer_email=email_address,
)
