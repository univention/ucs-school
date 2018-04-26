Import permissions
==================

To start an import or read data from previous imports, the user must be given permission.
Imports can only be made for a single role at a single school.

Import permission groups
------------------------

Permissions are stored in "Import Permission groups". Those are normal groups with an additional objectClass ``ucsschoolImportGroup``.
For a user to be allowed to start/read an import for role ``student`` at a school ``$OU``, a group must exist, that has the attributes::

	ucsschoolImportSchool: $OU
	ucsschoolImportRole: student
	users: $DN_of_user, ...

The above ``users`` property is how UDM shows it. An LDAP query would list the users DN in the attribute ``uniqueMember`` (and its UID in ``memberUid``).

``$OU-import-all`` groups
-------------------------

The join script ``40ucs-school-import-http-api.inst`` creates an import permission group with a name ``$OU-import-all`` *for each* OU.
For all OUs that are created later, the import hook ``/usr/share/ucs-school-import/hooks/ou_create_post.d/53importgroup_create`` will create such a group automatically.

Granularity
-----------

Those automatically created groups list all four roles (``student``, ``staff``, ``teacher_and_staff`` and ``teacher``).
Being member of such a group allows to run/read imports of users of all those roles in the referenced school/OU.

For finer-graned access control the administrator can create groups with less roles or remove roles from existing groups.

It is also possible to add more OUs to a group, to allow the same user(s) to run imports for multiple OUs.
It's not possible do do this in UMC, but on the command line.::

	$ OU=SchuleEins
	$ OU2=SchuleZwei
	$ OU3=SchuleDrei

	$ eval "$(ucr shell ldap/base)"

	$ udm groups/group modify \
	    --dn cn="$OU-import-all,cn=groups,ou=$OU,$ldap_base" \
	    --append ucsschoolImportSchool=$OU2 \
	    --append ucsschoolImportSchool=$OU3

.. _add-user-to-security-group:

Add user to security group
--------------------------

Create a school user that will be allowed to do imports (or don't, and use the ``Administrator`` user).
You can do this in the UMC Users-school-wizard.

Here is a code snippet how to do it on the command line (calling Python code).
In this example the OU is called ``SchuleEins`` and the username is ``myteacher``::

	$ python -c 'ou = "SchuleEins"; username = "myteacher" \
	    import univention.admin.uldap; \
	    from ucsschool.lib.models import Teacher;  \
	    lo, po = univention.admin.uldap.getAdminConnection(); \
	    t = Teacher(name=username, school=ou, firstname="my", lastname="teacher", password="univention"); \
	    print("Creation success: {!r}".format(t.create(lo))); \
	    print("DN: {!r}".format(t.dn))'

Add the user to the group of each OU you want to start an import for::

	$ udm groups/group modify \
	    --dn cn="$OU-import-all,cn=groups,ou=$OU,$ldap_base" \
	    --append users="uid=myteacher,cn=lehrer,cn=users,ou=$OU,$ldap_base"

An LDAP search should now look similar to this::

	$ univention-ldapsearch -LLL "cn=$OU-import-all" \
	    univentionPolicyReference ucsschoolImportRole ucsschoolImportSchool uniqueMember memberUid

	univentionPolicyReference: cn=schoolimport-all,cn=UMC,cn=policies,$ldap_base
	ucsschoolImportRole: student
	ucsschoolImportRole: staff
	ucsschoolImportRole: teacher_and_staff
	ucsschoolImportRole: teacher
	ucsschoolImportSchool: $OU
	uniqueMember: uid=myteacher,cn=lehrer,cn=users,ou=$OU,$ldap_base
	memberUid: myteacher

The user ``myteacher`` is now allowed to run imports (and read data of previous imports) on OU ``$OU`` for users of roles ``student``, ``staff``, ``teacher_and_staff`` and ``teacher``.
