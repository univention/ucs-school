import univention.test.ldapacls as utl

import univention.admin.uldap
import univention.admin.modules
import univention.admin.objects

class TestModule( utl.TestModule ):
	def __init__( self, **kwargs ):
		utl.TestModule.__init__( self, **kwargs )
		position=univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )

	def init( self ):

		# teacher
		self.teacher_lo = self._connect( self.user[ 'teacher' ].dn, 'univention' )
		if not self.teacher_lo:
			return False

		# admin
		self.admin_lo = self._connect( self.user[ 'admin' ].dn, 'univention' )
		if not self.admin_lo:
			return False

		return True

	def test( self ):
		success = []
		failed = []
		position=univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )

		# test 1: teacher adds student to another group
		student = univention.admin.objects.get( self.user_mod, utl.co, self.teacher_lo,
											   position = position, dn = self.school[ 'student' ].dn )

		student.open()
		student[ 'groups' ].append( self.school[ 'groups' ][ 0 ].dn )
		try:
			student.modify()
			if not self.different_schools:
				success.append( 'teacher could modify student group' )
			else:
				failed.append( 'teacher could modify student group' )
		except:
			if not self.different_schools:
				failed.append( 'teacher could not modify student group %s' % \
							   self.school[ 'groups' ][ 0 ].dn )
			else:
				success.append( 'teacher could not modify student group %s' % \
							   self.school[ 'groups' ][ 0 ].dn )

		# test 2: teacher adds student to a class (should fail)
		student = univention.admin.objects.get( self.user_mod, utl.co, self.teacher_lo,
											   position = position, dn = self.school[ 'student' ].dn )

		student.open()
		student[ 'groups' ].append( self.school[ 'class' ][ 1 ].dn )
		try:
			student.modify()
			failed.append( 'teacher could modify class group' )
		except:
			success.append( 'teacher could not modify class group' )

		# test 3: admin adds student to another group
		student = univention.admin.objects.get( self.user_mod, utl.co, self.admin_lo,
											   position = position, dn = self.school[ 'student' ].dn )

		student.open()
		student[ 'groups' ].append( self.school[ 'groups' ][ 1 ].dn )
		try:
			student.modify()
			if not self.different_schools:
				success.append( 'admin could modify student group' )
			else:
				failed.append( 'admin could modify student group' )
		except:
			if not self.different_schools:
				failed.append( 'admin could not modify student group %s' % \
							   self.school[ 'groups' ][ 0 ].dn )
			else:
				success.append( 'admin could not modify student group %s' % \
								self.school[ 'groups' ][ 0 ].dn )

		# test 4: admin adds student to a class (should fail)
		student = univention.admin.objects.get( self.user_mod, utl.co, self.admin_lo,
											   position = position, dn = self.school[ 'student' ].dn )

		student.open()
		student[ 'groups' ].append( self.school[ 'class' ][ 1 ].dn )
		try:
			student.modify()
			failed.append( 'admin could modify class group' )
		except:
			success.append( 'admin could not modify class group' )

		# test 5: admin creates student group (no class group)
		pos = "cn=schueler,cn=groups,ou=%s,%s" % ( self.school[ 'no' ], utl.ub[ 'ldap/base' ] )
		position.setDn( pos )
		dn = "cn=%s-%s,%s" % ( self.school[ 'no' ], 'Admin-Test', pos )
		group = univention.admin.objects.get( self.group_mod, utl.co, self.admin_lo,
											  position = position )
		group.open()
		group[ 'name' ] = '%s-Admin-Test' % self.school[ 'no' ]
		group[ 'description' ] = 'Admin Test'
		group[ 'sambaGroupType' ] = '2'
		try:
			group.create()
			if not self.different_schools:
				success.append( 'local admin created group %s' % dn )
			else:
				failed.append( 'local admin created group %s' % dn )
		except ( univention.admin.uexceptions.objectExists,
				 univention.admin.uexceptions.groupNameAlreadyUsed,
				 univention.admin.uexceptions.permissionDenied ):
			if not self.different_schools:
				failed.append( 'local admin is not allowed to create student group' )
			else:
				success.append( 'local admin is not allowed to create student group' )

		return ( success, failed )

	def cleanup( self ):
		# remove test group
		pos = "cn=schueler,cn=groups,ou=%s,%s" % ( self.school[ 'no' ], utl.ub[ 'ldap/base' ] )
		position = univention.admin.uldap.position( pos )
		dn = "cn=%s-%s,%s" % ( self.school[ 'no' ], 'Admin-Test', pos )
		group = univention.admin.objects.get( self.group_mod, utl.co, utl.lo,
											  position = position, dn = dn )
		group.open()
		try:
			group.remove()
		except:
			pass

		self.admin_lo.lo.lo.unbind()
		self.teacher_lo.lo.lo.unbind()
