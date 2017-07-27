from univention.admin.syntax import UDM_Objects, UDM_Attribute, select


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
		('student', _('Student')),
		('teacher', _('Teacher')),
		('staff', _('Staff')),
		('teacher_and_staff', _('Teacher and Staff')),
	]
