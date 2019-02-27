# -*- coding: utf-8 -*-

import time
import univention.testing.utils as utils
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase

try:
	from typing import Optional, Tuple
	from ucsschool.http_api.client import Client, ResourceRepresentation
except ImportError:
	pass


class HttpApiImportTester(ImportTestbase):

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

	def run_http_import_through_python_client(
			self,
			client,  # type: Client
			filename,  # type: str
			school,  # type: str
			role,  # type: str
			dryrun=True,  # type: Optional[bool]
			timeout=600  # type: Optional[int]
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
		:return: UserImportJob resource representation object
		:rtype: ResourceRepresentation.UserImportJobResource
		"""
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
