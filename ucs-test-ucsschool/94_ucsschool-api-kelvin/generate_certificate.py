#!/usr/bin/python3
#
# This script creates a CA and a certificate for the current fqdn.
# Please keep it simple, callling the script without arguments should just work ^tm

import argparse
import subprocess
import os
import socket


def parse_args():
	parser = argparse.ArgumentParser(description='Create a CA and a cert for the current fqdn')
	parser.add_argument(
		'--name-ca',
		default='myCA',
		help='name of the CA',
	)
	parser.add_argument(
		'--name-cert',
		default=socket.getfqdn(),
		help='fqdn of the cert to create',
	)
	args = parser.parse_args()
	return args


def create_CA(name='myCA'):
	private_key = '{name}.key'.format(name=name)
	if not os.path.isfile(private_key):
		print('Creating private key {private_key} for CA {name}'.format(private_key=private_key, name=name))
		subprocess.check_call(['openssl', 'genrsa', '-out', private_key, '2048'])
	else:
		print('Using existing private key {private_key} for CA {name}'.format(private_key=private_key, name=name))
	ca_cert = '{name}.pem'.format(name=name)
	if not os.path.isfile(ca_cert):
		print('Creating cert {ca_cert} for CA {name}'.format(ca_cert=ca_cert, name=name))
		subprocess.check_call([
			'openssl', 'req', '-x509', '-new', '-nodes',
			'-subj', '/C=DE/ST=Bremen/L=Bremen/O=univention/OU=dev/CN={name}'.format(name=name),
			'-key', private_key, '-sha256', '-days', '1825', '-out', ca_cert
		])
	else:
		print('Using existing cert {ca_cert} for CA {name}'.format(ca_cert=ca_cert, name=name))


def create_cert(name, ca_name):
	private_key = '{name}.key'.format(name=name)
	print('Create new private key {private_key} for {name}'.format(private_key=private_key, name=name))
	subprocess.check_call(['openssl', 'genrsa', '-out', private_key, '2048'])
	cert_req = '{name}.csr'.format(name=name)
	print('Create new cert req {cert_req} for {name}'.format(cert_req=cert_req, name=name))
	subprocess.check_call([
		'openssl', 'req', '-new', '-key', private_key,
		'-subj', '/C=DE/ST=Bremen/L=Bremen/O=univention/OU=dev/CN={name}'.format(name=name), '-out', cert_req
	])
	cert = '{name}.crt'.format(name=name)
	ca_cert = '{ca_name}.pem'.format(ca_name=ca_name)
	ca_key = '{ca_name}.key'.format(ca_name=ca_name)
	print('Create new cert {cert} for {name} using ca {ca_name}'.format(cert=cert, name=name, ca_name=ca_name))
	subprocess.check_call([
		'openssl', 'x509', '-req', '-in', cert_req, '-CA', ca_cert, '-CAkey', ca_key, '-CAcreateserial',
		'-out', cert, '-days', '1024', '-sha256'
	])


def main():
	args = parse_args()
	create_CA(name=args.name_ca)
	create_cert(args.name_cert, args.name_ca)


if __name__ == '__main__':
	main()
