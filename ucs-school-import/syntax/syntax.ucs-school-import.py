from univention.admin.syntax import UDM_Objects, UDM_Attribute, select
import univention.admin.localization

translation = univention.admin.localization.translation("univention-admin-syntax-ucsschool_import")
# The underscore function is already in use at this point -> use a different name
_local = translation.translate


class UCSSchool_Server_DN(UDM_Objects):
	udm_modules = ('computers/domaincontroller_master', 'computers/domaincontroller_backup', 'computers/domaincontroller_slave', 'computers/memberserver')
	label = '%(fqdn)s'
	empty_value = False
	simple = True


class ucsschoolSchools(UDM_Attribute):
	udm_module = 'container/ou'
	udm_filter = 'objectClass=ucsschoolOrganizationalUnit'
	attribute = 'name'
	label_format = '%(displayName)s'


class ucsschoolTypes(select):
	choices = [
		('student', _local('Student')),
		('teacher', _local('Teacher')),
		('staff', _local('Staff')),
		('teacher_and_staff', _local('Teacher and Staff')),
	]
