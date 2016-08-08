#!/usr/bin/python2.7
#
# UCS@School
#
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

import sys
import ldif
import argparse
import subprocess

import univention.admin.uldap

def normalize_permission(perms):
	level_to_priv = {
		'none': '0',
		'disclose': 'd',
		'auth': 'xd',
		'compare': 'cxd',
		'search': 'scxd',
		'read': 'rscxd',
		'write': 'wrscxd',
		'add': 'arscxd',
		'delete': 'zrscxd',
		'manage': 'mwrscxd',
	}
	if not perms.startswith('='):
		perms = '=%s' % level_to_priv[perms.split('(', 1)[0]]
	return perms


def parse_acls(args, lo):
	if isinstance(args.output, basestring):
		args.output = open(args.output, 'wb')
	entries = lo.search(base=args.base)

	writer = ldif.LDIFWriter(args.output)
	code = 0
	for dn, attrs in entries:
		entry = {}
		for attr in attrs:
			# TODO: replace subprocess by some C calls to improove speed
			process = subprocess.Popen(['slapacl', '-d0', '-D', args.binddn, '-b', dn, attr], stderr=subprocess.PIPE)
			_, stderr = process.communicate()
			for line in stderr.splitlines():
				if line.startswith('%s: ' % (attr,)):
					entry.setdefault(attr, []).append(normalize_permission(line.split(': ', 1)[-1].strip()))
			try:
				entry[attr]
			except KeyError as exc:
				print >> sys.stderr, dn, exc
				code = 1
		writer.unparse(dn, entry)
	return code


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-b', '--base')
	parser.add_argument('-o', '--output', default=sys.stdout)
	parser.add_argument('binddn')
	args = parser.parse_args()
	lo, po = univention.admin.uldap.getAdminConnection()
	sys.exit(parse_acls(args, lo))


if __name__ == '__main__':
	main()
