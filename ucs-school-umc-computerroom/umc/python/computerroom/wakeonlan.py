#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# WakeOnLan/WOL helpers
#
# Copyright 2019 Univention GmbH
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

from __future__ import absolute_import

import netifaces
import socket

BROADCAST_IP = '255.255.255.255'
DEFAULT_PORT = 9


def get_local_ip_addresses(blacklisted_interfaces=None, blacklisted_interface_prefixes=None):
	# type: (Optional[Iterable[str]], Optional[Iterable[str]]) -> Set[str]
	"""
	Returns a list of local IPv4 addresses.

	:param blacklisted_interfaces: iterable that returns a list of interface names that shall be ignored
	:type blacklisted_interfaces: None or Iterable[str]
	:param blacklisted_interface_prefixes: iterable that returns a list of interface prefixes that shall be ignored
	:type blacklisted_interface_prefixes: None or Iterable[str]
	:return: list of IPv4 addresses
	:rtype: Set[str]
	"""
	result = set()  # type: Set[str]
	for interface_name in netifaces.interfaces():
		if blacklisted_interfaces is not None and interface_name in blacklisted_interfaces:
			continue
		if blacklisted_interface_prefixes is not None and any([interface_name.startswith(prefix) for prefix in blacklisted_interface_prefixes]):
			continue
		iface_info = netifaces.ifaddresses(interface_name)
		af_inet_addr = iface_info.get(netifaces.AF_INET, [{}])[0].get('addr')
		if af_inet_addr is not None:
			result.add(af_inet_addr)
	return result


def send_wol_packet(mac_address, blacklisted_interfaces=None, blacklisted_interface_prefixes=None):
	# type: (str, Optional[Iterable[str]], Optional[Iterable[str]]) -> None
	"""
	Sends a WakeOnLan packet to the specified MAC address via
	all interfaces (that are not blacklisted).
	>>> send_wol_packet(
	...	  '12:34:56:78:9A:BC',
	...	  blacklisted_interfaces=['lo'],
	...	  blacklisted_interface_prefixes=['tun', 'docker'])
	>>>

	:param mac_address: MAC address of the target host
	:type mac_address: str
	:param blacklisted_interfaces: iterable that returns a list of interface names that shall be ignored
	:type blacklisted_interfaces: None or Iterable[str]
	:param blacklisted_interface_prefixes: iterable that returns a list of interface prefixes that shall be ignored
	:type blacklisted_interface_prefixes: None or Iterable[str]
	"""

	# remove usual delimiter characters
	addr = mac_address
	for c in '.:-':
		addr = addr.replace(c, '')

	# check MAC address validity
	if len(addr) != 12:
		raise ValueError('Invalid MAC address specified: {}'.format(mac_address))
	try:
		bytearray.fromhex(addr.encode())
	except ValueError as exc:
		raise ValueError('Invalid MAC address specified: {}: {}'.format(mac_address, exc))

	# generate payload
	payload_hex = 'FFFFFFFFFFFF' + (addr * 16).encode()
	payload = bytes(bytearray.fromhex(payload_hex))

	for local_addr in get_local_ip_addresses(blacklisted_interfaces, blacklisted_interface_prefixes):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		sock.bind((local_addr, 0))
		sock.connect((BROADCAST_IP, DEFAULT_PORT))
		sock.send(payload)
		sock.close()


if __name__ == '__main__':
	send_wol_packet(
		'12:34:56:78:9A:BC',
		blacklisted_interfaces=['lo'],
		blacklisted_interface_prefixes=['tun', 'docker'])
