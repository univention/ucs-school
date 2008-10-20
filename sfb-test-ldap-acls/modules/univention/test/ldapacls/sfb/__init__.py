import datetime
import os
import ldap
from optparse import Option

import univention.admin.uldap
import univention.admin.modules
import univention.admin.objects
import univention.admin.handlers.users.user
import univention.admin.handlers.groups.group
import univention.admin.handlers.container.ou

import univention.test.ldapacls as utl

import selreplica
import passwd
import groups
import rejoin

import univention.debug as ud

ud.init( '/var/log/univention/test-ldapacls-sfb.log', 1, 1 )

school1 = { 'no' : '799',
			'dc' : None,
			'pwd-policy' : None,
			'teacher' : None,
			'student' : None,
			'student-userexpiry' : None,
			'student-passwordexpiry' : None,
			'class' : [],
			'groups' : [],
			'admin' : None }

school2 = { 'no' : '798',
			'dc' : None,
			'pwd-policy' : None,
			'teacher' : None,
			'student' : None,
			'student-userexpiry' : None,
			'student-passwordexpiry' : None,
			'class' : [],
			'groups' : [],
			'admin' : None }

def get_options():
	return ( Option( '-1', '--sfb-school1', action = 'store', dest = 'school1_no', default = '799',
					 help = 'set number for the first test school' ),
			 Option( '-2', '--sfb-school2', action = 'store', dest = 'school2_no', default = '798',
					 help = 'set number for the second test school' ),
			 Option( '--remove-ou', action = 'store_true', dest = 'remove_ou', default = False,
					 help = 'remove containers and ou during cleanup' ))

def init():
	global school1, school2

	school1[ 'no' ] = utl.options.school1_no
	school2[ 'no' ] = utl.options.school2_no

	position = univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )
	user_mod = univention.admin.modules.get( 'users/user' )
	univention.admin.modules.init( utl.lo, position, user_mod )
	group_mod = univention.admin.modules.get( 'groups/group' )
	univention.admin.modules.init( utl.lo, position, group_mod )
	pwdpolicy_mod = univention.admin.modules.get( 'policies/pwhistory' )
	univention.admin.modules.init( utl.lo, position, pwdpolicy_mod )
	for school in ( school1, school2 ):
		school_base = 'ou=%s,%s' % ( school[ 'no' ], utl.ub[ 'ldap/base' ] )
		res = os.system( '/usr/local/sbin/SFB_import/create_ou %s >/dev/null' % school[ 'no' ] )

		# set DC password
		dn = "cn=dc%s,cn=dc,cn=server,cn=computers,%s" % ( school[ 'no' ], school_base )
		mod = univention.admin.modules.get( 'computers/domaincontroller_slave' )
		dc = univention.admin.objects.get( mod, utl.co, utl.lo, position = position, dn = dn )
		dc.open()
		dc[ 'password' ] = 'univention'
		dc.modify()
		school[ 'dc' ] = dc

		pos = "cn=groups,%s" % school_base
		position.setDn( pos )
		dn = "cn=Domain Users %s,%s" % ( school[ 'no' ], pos )
		clss = univention.admin.objects.get( group_mod, utl.co, utl.lo,
											 position = position )
		clss.open()
		if clss.exists():
			print 'GIBT\'S SCHON'

		clss[ 'name' ] = 'Domain Users %s' % school[ 'no' ]
		clss[ 'sambaGroupType' ] = '2'
		try:
			clss.create()
			utl.info( 'created %s' % dn )
		except ( univention.admin.uexceptions.objectExists,
				 univention.admin.uexceptions.groupNameAlreadyUsed ):
			clss.dn = dn
			clss.modify()
			utl.info( 'already exists %s' % dn )

		# create classes
		pos = "cn=klassen,cn=schueler,cn=groups,%s" % school_base
		position.setDn( pos )
		for class_no in ( '1A', '2B' ):
			dn = "cn=%s-%s,%s" % ( school[ 'no' ], class_no, pos )
			clss = univention.admin.objects.get( group_mod, utl.co, utl.lo,
												  position = position )
			clss.open()
			clss[ 'name' ] = '%s-%s' % ( school[ 'no' ], class_no )
			clss[ 'description' ] = 'Klasse %s' % class_no
			clss[ 'sambaGroupType' ] = '2'
			try:
				clss.create()
				utl.info( 'created %s' % dn )
			except ( univention.admin.uexceptions.objectExists,
					 univention.admin.uexceptions.groupNameAlreadyUsed ), e:
				utl.critical( str( e ) )
				utl.info( 'already exists %s' % dn )
			school[ 'class' ].append( clss )

		# create student groups
		pos = "cn=schueler,cn=groups,%s" % school_base
		position.setDn( pos )
		for grp in ( 'Test01', 'Test02' ):
			dn = "cn=%s-%s,%s" % ( school[ 'no' ], grp, pos )
			group = univention.admin.objects.get( group_mod, utl.co, utl.lo,
												  position = position )
			group.open()
			group[ 'name' ] = '%s-%s' % ( school[ 'no' ], grp )
			group[ 'description' ] = 'Schueler Gruppe %s' % grp
			group[ 'sambaGroupType' ] = '2'
			try:
				group.create()
				utl.info( 'created %s' % dn )
			except ( univention.admin.uexceptions.objectExists,
					 univention.admin.uexceptions.groupNameAlreadyUsed ):
				utl.info( 'already exists %s' % dn )
			school[ 'groups' ].append( group )

		# create teacher account
		pos = "cn=lehrer,cn=users,%s" % school_base
		position.setDn( pos )
		dn = "uid=teacher01-%s,%s" % ( school[ 'no' ], pos )
		grp_dns = [ "cn=Domain Users %s,cn=groups,%s" % ( school[ 'no' ], school_base ) ]
		grp_dns.append( "cn=lehrer%s,cn=groups,%s" % ( school[ 'no' ], school_base ) )
		teacher = univention.admin.objects.get( user_mod, utl.co, utl.lo,
												position = position )
		teacher.open()
		teacher[ 'username' ] = 'teacher01-%s' % school[ 'no' ]
		teacher[ 'primaryGroup' ] = grp_dns[ 0 ]
		teacher[ 'groups' ] = grp_dns[ 1 : ]
		teacher[ 'password' ] = 'univention'
		teacher[ 'lastname' ] = 'Teacher 01'
		teacher[ 'unixhome' ] = '/home/%s' % teacher[ 'username' ]
		teacher[ 'overridePWHistory' ] = '1'
		try:
			teacher.create()
			utl.info( 'created %s' % dn )
		except ( univention.admin.uexceptions.objectExists,
				 univention.admin.uexceptions.uidAlreadyUsed ):
			utl.info( 'already exists %s' % dn )

		school[ 'teacher' ] = teacher

		## create student accounts
		# normal student account
		position.setDn( "cn=schueler,cn=users,%s" % school_base )
		dn = "uid=student01-%s,cn=schueler,cn=users,%s" % ( school[ 'no' ], school_base )
		grp_dns = [ "cn=Domain Users %s,cn=groups,%s" % ( school[ 'no' ], school_base ) ]
		grp_dns.append( "cn=schueler%s,cn=groups,%s" % ( school[ 'no' ], school_base ) )
		grp_dns.append( "cn=%s-1A,cn=klassen,cn=schueler,cn=groups,%s" % \
						( school[ 'no' ], school_base ) )
		student = univention.admin.objects.get( user_mod, utl.co, utl.lo,
											  position = position )
		student.open()
		student[ 'username' ] = 'student01-%s' % school[ 'no' ]
		student[ 'primaryGroup' ] = grp_dns[ 0 ]
		student[ 'groups' ] = grp_dns[ 1 : ]
		student[ 'unixhome' ] = '/home/student01'
		student[ 'password' ] = 'univention'
		student[ 'lastname' ] = 'Student 01'
		student[ 'overridePWHistory' ] = '1'
		try:
			student.create()
			utl.info( 'created %s' % dn )
		except ( univention.admin.uexceptions.objectExists,
				 univention.admin.uexceptions.uidAlreadyUsed ):
			utl.info( 'already exists %s' % dn )

		school[ 'student' ] = student


		# create student accounts with password expire date
		today = datetime.datetime.now()
		oneday = datetime.timedelta( 1 )
		dn = "cn=pwd-expire-%s,cn=policies,%s" % ( school[ 'no' ], school_base )
		policy = univention.admin.objects.get( pwdpolicy_mod, utl.co, utl.lo,
											   position = position )
		policy[ 'name' ] = 'pwd-expire-%s' % school[ 'no' ]
		policy[ 'expiryInterval' ] =  '5'
		try:
			policy.create()
		except:
			try:
				policy.modify()
			except:
				pass
		school[ 'pwd-policy' ] = policy

		dn = "uid=student02-pwd-expire-%s,cn=schueler,cn=users,%s" % ( school[ 'no' ], school_base )
		grp_dns = [ "cn=Domain Users %s,cn=groups,%s" % ( school[ 'no' ], school_base ) ]
		grp_dns.append( "cn=schueler%s,cn=groups,%s" % ( school[ 'no' ], school_base ) )
		grp_dns.append( "cn=%s-1A,cn=klassen,cn=schueler,cn=groups,%s" % \
						( school[ 'no' ], school_base ) )
		student = univention.admin.objects.get( user_mod, utl.co, utl.lo,
											  position = position )
		student.open()
		student[ 'username' ] = 'student02-pwd-expire-%s' % school[ 'no' ]
		student[ 'primaryGroup' ] = grp_dns[ 0 ]
		student[ 'groups' ] = grp_dns[ 1 : ]
		student[ 'unixhome' ] = '/home/student02'
		student[ 'password' ] = 'univention'
		student[ 'lastname' ] = 'Student 02'
		student[ 'overridePWHistory' ] = '1'
		univention.admin.objects.replacePolicyReference( student, 'policies/pwhistory', policy.dn )

		try:
			student.create()
			utl.info( 'created %s' % dn )
		except ( univention.admin.uexceptions.uidAlreadyUsed,
				 univention.admin.uexceptions.objectExists ):
			utl.info( 'already exists %s' % dn )

		school[ 'student-userexpiry' ] = student

		# create student accounts with account expire date
		dn = "uid=student03-user-expire-%s,cn=schueler,cn=users,%s" % ( school[ 'no' ], school_base )
		grp_dns = [ "cn=Domain Users %s,cn=groups,%s" % ( school[ 'no' ], school_base ) ]
		grp_dns.append( "cn=schueler%s,cn=groups,%s" % ( school[ 'no' ], school_base ) )
		grp_dns.append( "cn=%s-1A,cn=klassen,cn=schueler,cn=groups,%s" % \
						( school[ 'no' ], school_base ) )
		student = univention.admin.objects.get( user_mod, utl.co, utl.lo,
											  position = position )
		student.open()
		student[ 'username' ] = 'student03-user-expire-%s' % school[ 'no' ]
		student[ 'primaryGroup' ] = grp_dns[ 0 ]
		student[ 'groups' ] = grp_dns[ 1 : ]
		student[ 'unixhome' ] = '/home/student03'
		student[ 'password' ] = 'univention'
		student[ 'lastname' ] = 'Student 03'
		student[ 'overridePWHistory' ] = '1'
		tomorrow = today  + oneday
		student[ 'userexpiry' ] = '%02d.%02d.%s' % ( tomorrow.day, tomorrow.month,
													 str( tomorrow.year )[ -2 : ] )

		try:
			student.create()
			utl.info( 'created %s' % dn )
		except ( univention.admin.uexceptions.uidAlreadyUsed,
				 univention.admin.uexceptions.objectExists ):
			utl.info( 'already exists %s' % dn )

		school[ 'student-passwordexpiry' ] = student

		# create admin account
		position.setDn( "cn=admins,cn=users,%s" % school_base )
		dn = "uid=admin01-%s,cn=admins,cn=users,%s" % ( school[ 'no' ], school_base )
		grp_dn = "cn=admins%s,cn=ouadmins,cn=groups,%s" % \
				 ( school[ 'no' ], utl.ub[ 'ldap/base' ] )
		admin = univention.admin.objects.get( user_mod, utl.co, utl.lo,
											  position = position )
		admin.open()
		admin[ 'username' ] = 'admin01-%s' % school[ 'no' ]
		admin[ 'primaryGroup' ] = grp_dn
		admin[ 'unixhome' ] = '/home/admin01'
		admin[ 'password' ] = 'univention'
		admin[ 'lastname' ] = 'Admin 01'
		admin[ 'overridePWHistory' ] = '1'
		try:
			admin.create()
			utl.info( 'created %s' % dn )
		except ( univention.admin.uexceptions.uidAlreadyUsed,
				 univention.admin.uexceptions.objectExists ):
			utl.info( 'already exists %s' % dn )

		school[ 'admin' ] = admin

	return True

def __test( mod, success, description, **kwargs ):
	test = mod.TestModule( **kwargs )
	if test.init():
		utl.important( 'test group: %s' % description )
		if not success:
			neg, pos = test.test()
		else:
			pos, neg = test.test()
		if pos:
			utl.important( ' OK:' )
			for msg in pos:
				utl.info( '	 ' + msg )
		if neg:
			utl.error( ' FAILED:' )
			for msg in neg:
				utl.error( '  ' + msg )
		test.cleanup()

def run():
	global school1, school2

	# replication tests
	utl.info( '>> running %s test' % selreplica.__name__ )
	__test( selreplica, True, 'DC slave can read its own ou',
			user = school1, school = school1 )
	__test( selreplica, True, 'DC slave can read its own ou',
			user = school2, school = school2 )
	__test( selreplica, False, 'DC slave tries to read another ou',
			user = school1, school = school2 )
	__test( selreplica, False, 'DC slave tries to read another ou',
			user = school2, school = school1 )
	utl.info( '<< %s test finished' % selreplica.__name__ )

	# password tests
	utl.info( '>> running %s test' % passwd.__name__ )
	__test( passwd, True, 'users try to change password at their school',
			user = school1, school = school1, different_schools = False )
	__test( passwd, True, 'users try to change passwords at another school',
			user = school1, school = school2, different_schools = True )
	utl.info( '<< %s test finished' % passwd.__name__ )

	# group tests
	utl.info( '>> running %s test' % groups.__name__ )
	__test( groups, True, 'users try to modify groups at their school',
			user = school1, school = school1, different_schools = False )
	__test( groups, True, 'users try to modify groups at another school',
			user = school1, school = school2, different_schools = True )
	utl.info( '<< %s test finished' % groups.__name__ )

	# rejoin tests
	utl.info( '>> running %s test' % rejoin.__name__ )
	__test( rejoin, True, 'local admin re-joins a DC slave',
			user = school1, school = school1, different_schools = False )
	__test( rejoin, True, 'local admin re-joins a DC slave at another school',
			user = school1, school = school2, different_schools = True )
	utl.info( '<< %s test finished' % rejoin.__name__ )

	utl.important( '>>>> make DC slave of school1 handle school2' )
	# make DC slave of school1 handle school2
	position = univention.admin.uldap.position( utl.ub[ 'ldap/base' ] )
	ou_mod = univention.admin.modules.get( 'container/ou' )
	univention.admin.modules.init( utl.lo, position, ou_mod )
	dn = "ou=%s,%s" % ( school2[ 'no' ], utl.ub[ 'ldap/base' ] )
	ou = univention.admin.objects.get( ou_mod, utl.co, utl.lo, position = position, dn = dn )
	ou.open()
	ou[ 'OU-ACL-Write' ] = school1[ 'dc' ].dn
	try:
		ou.modify()
	except:
		utl.error( 'already exists %s' % dn )

	# replication tests
	utl.info( '>> running %s test' % selreplica.__name__ )
	__test( selreplica, True, 'DC slave can read its own ou',
			user = school1, school = school1 )
	__test( selreplica, True, 'DC slave can read its own ou',
			user = school2, school = school2 )
	__test( selreplica, True, 'DC slave tries to read another ou',
			user = school1, school = school2 )
	__test( selreplica, False, 'DC slave tries to read another ou',
			user = school2, school = school1 )
	utl.info( '<< %s test finished' % selreplica.__name__ )

	# password tests
	utl.info( '>> running %s test' % passwd.__name__ )
	__test( passwd, True, 'users try to change password at their school',
			user = school1, school = school1, different_schools = False )
	__test( passwd, True, 'users try to change passwords at another school',
			user = school1, school = school2, different_schools = True )
	utl.info( '<< %s test finished' % passwd.__name__ )

	# group tests
	utl.info( '>> running %s test' % groups.__name__ )
	__test( groups, True, 'users try to modify groups at their school',
			user = school1, school = school1, different_schools = False )
	__test( groups, True, 'users try to modify groups at another school',
			user = school1, school = school2, different_schools = True )
	utl.info( '<< %s test finished' % groups.__name__ )

	# rejoin tests
	utl.info( '>> running %s test' % rejoin.__name__ )
	__test( rejoin, True, 'local admin re-joins a DC slave',
			user = school1, school = school1, different_schools = False )
	__test( rejoin, True, 'local admin re-joins a DC slave at another school',
			user = school1, school = school2, different_schools = True )
	utl.info( '<< %s test finished' % rejoin.__name__ )


def cleanup():
	for school in ( school1, school2 ):
		host = 'LDAP://' + utl.ub[ 'ldap/master' ]
		dc_lo = ldap.ldapobject.SmartLDAPObject( uri = host, who = utl.admin,
												 cred = utl.password, start_tls = 0 )
		filterstr = '(&(!(objectClass=organizationalUnit))(!(objectClass=organizationalRole)))'
		if utl.options.remove_ou:
			filterstr = '(objectClass=*)'
		try:
			# remove all objects but containers and organisational units
			res = dc_lo.search_s( 'ou=%s,%s' % ( school[ 'no' ], utl.ub[ 'ldap/base' ] ),
								  ldap.SCOPE_SUBTREE,
								  filterstr=filterstr )
		except ldap.NO_SUCH_OBJECT:
			continue

		failed = []
		for item in res:
			try:
				dc_lo.delete_s( item[ 0 ] )
				utl.info( 'deleted %s' % item[ 0 ] )
			except:
				failed.append( item[ 0 ] )
		while failed:
			failed_again = []
			for item in failed:
				try:
					dc_lo.delete_s( item )
					utl.info( 'Deleted %s' % item )
				except Exception, e:
					utl.info( 'Deletion failed again: %s' % item )
					failed_again.append( item )
			failed = failed_again
	return True
