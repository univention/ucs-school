class UCSSchool_Server_DN( UDM_Objects ):
	udm_modules = ( 'computers/domaincontroller_master', 'computers/domaincontroller_backup', 'computers/domaincontroller_slave', 'computers/memberserver' )
	label = '%(fqdn)s'
	empty_value = False
	simple = True


class ucsschoolSchools(UDM_Attribute):
	udm_module = 'container/ou'
	udm_filter = 'objectClass=ucsschoolOrganizationalUnit'
	attribute = 'name'
	label_format = '%(displayName)s'
