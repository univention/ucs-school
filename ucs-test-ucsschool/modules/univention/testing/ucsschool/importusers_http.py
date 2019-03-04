# -*- coding: utf-8 -*-

import os
import json
import time
import tempfile
import univention.testing.utils as utils
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase

try:
	from typing import Dict, Optional, Tuple
	from ucsschool.http_api.client import Client, ResourceRepresentation
except ImportError:
	pass


class HttpApiImportTester(ImportTestbase):
	default_config_path = '/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json'
	_default_config = {}

	def create_import_security_group(
			self,
			ou_dn,  # type: str
			allowed_ou_names=None,  # type: Optional[List[str]]
			roles=None,  # type: Optional[List[str]]
			user_dns=None  # type: Optional[List[str]]
	):
		# type: (...) -> Tuple[str, str]
		"""
		Create a import security group.

		:param str ou_dn: DN of OU in which to store the group
		:param list allowed_ou_names: list of OU names, none if None
		:param list roles: list of user roles (staff, student...), all if None
		:param list user_dns: list of DNs of users to add to group, none if None
		:return: group_dn, group_name
		:rtype: Tuple[str, str]
		"""
		allowed_ou_names = [] if allowed_ou_names is None else allowed_ou_names
		roles = self.all_roles if roles is None else roles
		user_dns = [] if user_dns is None else user_dns

		group_dn, group_name = self.udm.create_group(
			position='cn=groups,{}'.format(ou_dn),
			options=['posix', 'samba', 'ucsschoolImportGroup'],
			append={
				'users': user_dns,
				'ucsschoolImportRole': roles,
				'ucsschoolImportSchool': allowed_ou_names,
			}
		)
		utils.verify_ldap_object(
			group_dn,
			expected_attr={
				'cn': [group_name],
				'ucsschoolImportRole': roles,
				'ucsschoolImportSchool': allowed_ou_names,
				'uniqueMember': user_dns
			},
			strict=False,
			should_exist=True
		)
		return group_dn, group_name

	@property
	def default_config(self):
		if not self._default_config:
			with open(self.default_config_path, 'r') as fp:
				self._default_config.update(json.load(fp))
		return self._default_config

	def run_http_import_through_python_client(
			self,
			client,  # type: Client
			filename,  # type: str
			school,  # type: str
			role,  # type: str
			dryrun=True,  # type: Optional[bool]
			timeout=600,  # type: Optional[int]
			config=None,  # type: Optional[Dict[str, str]]
	):
		# type: (...) -> ResourceRepresentation.UserImportJobResource
		"""
		Run an import through the Python client of the HTTP-API.

		:param ucsschool.http_api.client.Client client: an instance of ucsschool.http_api.client.Client
		:param str filename: the CSV file to import
		:param str school: OU to import into
		:param str role: UCS@school user role
		:param bool dryrun: whether to do a dry-run or a real import
		:param int timeout: seconds to wait for the import to finish
		:param dict config: if not None: configuration to temporarily write to
			`/var/lib/ucs-school-import/configs/user_import_http-api.json`
		:return: UserImportJob resource representation object
		:rtype: ResourceRepresentation.UserImportJobResource
		"""
		if not config and config is not None:
			self.log.warn('Empty "config" passed!')
		with TempHttpApiConfig(config):
			t0 = time.time()
			import_job = client.userimportjob.create(
				filename=filename,
				school=school,
				user_role=role,
				dryrun=dryrun
			)
			while time.time() - t0 < timeout:
				job = client.userimportjob.get(import_job.id)  # type: ResourceRepresentation.UserImportJobResource
				if job.status in ('Finished', 'Aborted'):
					return job
				if job.result and isinstance(job.result.result, dict):
					progress = float(job.result.result.get('percentage', 0.0))
				else:
					progress = 0.0
				self.log.debug(
					'Waiting for import job %r to finish (%d%% - %d/%ds)...',
					import_job.id,
					int(progress),
					int(time.time() - t0),
					timeout
				)
				time.sleep(1)
			else:
				utils.fail('Import job did not finish in {} seconds.'.format(timeout))

	def fail(self, msg, returncode=1, import_job=None):
		"""
		Print import jobs logfile, then print package versions, traceback and
		error message.
		"""
		if import_job:
			self.log.debug('------ Start logfile of job %r ------', import_job.id)
			self.log.debug(import_job.log_file)
			self.log.debug('------ End logfile of job %r ------', import_job.id)
		else:
			self.log.debug('No import_job - no logfile.')
		return super(HttpApiImportTester, self).fail(msg, returncode)


class TempHttpApiConfig(object):
	default_config_path = '/var/lib/ucs-school-import/configs/user_import_http-api.json'

	def __init__(self, config):
		self.config = config
		if config is not None:
			_fd, self.original_config_backup = tempfile.mkstemp(dir=os.path.dirname(self.default_config_path))

	def __enter__(self):
		if self.config is None:
			return
		# copy original to backup file. copy only content, leaving permissions intact.
		with open(self.original_config_backup, 'w') as fpw:
			with open(self.default_config_path, 'r') as fpr:
				fpw.write(fpr.read())
		with open(self.default_config_path, 'w') as fpw:
			json.dump(self.config, fpw)

	def __exit__(self, exc_type, exc_val, exc_tb):
		if self.config is None:
			return
		with open(self.default_config_path, 'w') as fpw:
			with open(self.original_config_backup, 'r') as fpr:
				fpw.write(fpr.read())
		os.remove(self.original_config_backup)
