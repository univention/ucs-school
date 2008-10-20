import univention.test.ldapacls as utl

import univention.admin.uldap
import univention.admin.modules
import univention.admin.objects

class TestModule( utl.TestModule ):
	def __init__( self, **kwargs ):
		utl.TestModule.__init__( self, **kwargs )

	def init( self ):
		# student
		self.student_lo = self._connect( self.user[ 'student' ].dn, 'univention' )
		if not self.student_lo:
			return False

		self.student_uexpiry_lo = self._connect( self.user[ 'student-userexpiry' ].dn, 'univention' )
		if not self.student_uexpiry_lo:
			return False

		self.student_pexpiry_lo = self._connect( self.user[ 'student-passwordexpiry' ].dn,
												 'univention' )
		if not self.student_pexpiry_lo:
			return False

		# teacher
		self.teacher_lo = self._connect( self.user[ 'teacher' ].dn, 'univention' )
		if not self.teacher_lo:
			return False

		# admin
		self.admin_lo = self._connect( self.user[ 'admin' ].dn, 'univention' )
		if not self.admin_lo:
			return False

		# dc
		self.dc_lo = self._connect( self.user[ 'dc' ].dn, 'univention' )
		if not self.dc_lo:
			return False

		return True

	def test( self ):
		success = []
		failed = []
		position=univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )

		# test 1: student changes his password
		res = self._change_password( self.student_lo, position, 'student', 'student',
									 self.school[ 'student' ].dn,
									 should_fail = self.different_schools )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		res = self._change_password( self.student_lo, position, 'student', 'teacher',
									 self.school[ 'teacher' ].dn, should_fail = True )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		res = self._change_password( self.student_lo, position, 'student', 'admin',
									 self.school[ 'admin' ].dn, should_fail = True )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		res = self._change_password( self.student_uexpiry_lo, position, 'student-userexpiry',
									 'student-userexpiry', self.school[ 'student-userexpiry' ].dn,
									 should_fail = self.different_schools )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		res = self._change_password( self.student_pexpiry_lo, position, 'student-passwordexpiry',
									 'student-passwordexpiry',
									 self.school[ 'student-passwordexpiry' ].dn,
									 should_fail = self.different_schools )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		# test 2: teacher changes password of student, admin (should fail) and his own
		res = self._change_password( self.teacher_lo, position, 'teacher', 'student',
									 self.school[ 'student' ].dn,
									 should_fail = self.different_schools )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		res = self._change_password( self.teacher_lo, position, 'teacher', 'teacher',
									 self.school[ 'teacher' ].dn,
									 should_fail = self.different_schools )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		res = self._change_password( self.teacher_lo, position, 'teacher', 'admin',
									 self.school[ 'admin' ].dn, should_fail = True )
		if res[ 0 ]:
			success.append( res[ 1 ] )
		else:
			failed.append( res[ 1 ] )

		# test 3: dc changes password of teacher, student, admin
		for user in ( 'student', 'teacher', 'admin' ):
			res = self._change_password( self.dc_lo, position, 'DC', user, self.school[ user ].dn,
										 should_fail = self.different_schools )
			if res[ 0 ]:
				success.append( res[ 1 ] )
			else:
				failed.append( res[ 1 ] )

		# test 4: admin changes password of teacher, student, admin
		for user in ( 'student', 'teacher', 'admin' ):
			res = self._change_password( self.admin_lo, position, 'admin', user,
										 self.school[ user ].dn,
										 should_fail = self.different_schools )
			if res[ 0 ]:
				success.append( res[ 1 ] )
			else:
				failed.append( res[ 1 ] )

		return ( success, failed )

	def cleanup( self ):
		position=univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )
		# reset passwords
		for user in ( 'student', 'teacher', 'admin', 'student-passwordexpiry', 'student-userexpiry' ):
			self._change_password( utl.lo, position, 'cn=admin', user, self.school[ user ].dn,
								   passwd = 'univention' )
		self.admin_lo.lo.lo.unbind()
		self.teacher_lo.lo.lo.unbind()
		self.student_lo.lo.lo.unbind()
		self.dc_lo.lo.lo.unbind()
