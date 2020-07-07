Single source, partial import (SiSoPi) scenario
===============================================

The scenario in which a single source database for users in all schools exists, but the user import jobs will be run separately for each school, is supported since UCS\@school 4.3 v5 for both the command line and the HTTP-API import (via UMC module).

Implemented in Bug 47447: https://forge.univention.org/bugzilla/show_bug.cgi?id=47447

Requirements
------------

* A single source database exists, that knows all users and has globally unique recordUIDs for them.
* OU spanning user accounts (a user can be member of multiple schools).
* The source database exports separate CSV files per school and user type.
* Each school imports its users separately at a time and order of their choosing.
* As imports are done in random order, it is possible that to move a user from one school to another, it is first removed in one school and imported at the other school at a later time. The user account must not be deleted in the meantime.

Implementation
--------------

* When importing, the users of the same source database (same sourceUID) that are not in the CSV file should not be deleted:
  * When searching for existing users to delete (because they are missing in the CSV file), only those users that are part of the importing school should be considered.
  * Users that normally would be deleted (or deactivated), will be immediately deactivated and moved to a temporary OU (henceforth called "limbo" OU/school) instead.
* If a user is to be created in the importing school, a search for a user with its recordUID is done. If it exists in any school of the domain (including the limbo school), the school being imported is added to its ``schools`` attribute. If the user was in the limbo school, it's removed from there and thus moved from it to the school being imported.

Setup
-----

Create the ``limbo`` OU::

    /usr/share/ucs-school-import/scripts/create_ou limbo

Create an import configuration in ``/var/lib/ucs-school-import/configs/user_import.json``::

    {
        "classes": {
            "user_importer": "ucsschool.importer.mass_import.sisopi_user_import.SingleSourcePartialUserImport"
        },
        "configuration_checks": ["defaults", "sisopi"],
        "csv": {
                "mapping": {
                    "firstname": "firstname",
                    "lastname": "lastname",
                    "record_uid": "record_uid",
                    "classes": "school_classes"
                }
            },
            "scheme": {
                "username": {
                    "default": "<firstname>.<lastname>[ALWAYSCOUNTER]"
                }
        },
        "deletion_grace_period": {
            "deactivation": 0,
            "deletion": 90
        },
        "limbo_ou": "limbo",
        "source_uid": "TESTID",
        "user_role": "student"
    }

Test: create and delete
-----------------------

Create two CSV files (``/tmp/sisopi1.csv `` and ``/tmp/sisopi_none.csv``)::

    cat /tmp/sisopi1.csv
    "firstname","lastname","record_uid","classes"
    "peter","silie","peter.silie","igel"

    root@m70:~# cat /tmp/sisopi_none.csv
    "firstname","lastname","record_uid","classes"

Importing the first CSV will create a student in the OU ``DEMOSCHOOL``::

    /usr/share/ucs-school-import/scripts/ucs-school-user-import -v -s DEMOSCHOOL -i /tmp/sisopi1.csv
    [..]
    user_import.log_stats:742  Created ImportStudent: 1
    user_import.log_stats:742    ['peter.silie1']

When importing the CSV without the user, it should be deleted.
It will however be moved to the ``limbo`` OU instead::

    /usr/share/ucs-school-import/scripts/ucs-school-user-import -v -s DEMOSCHOOL -i /tmp/sisopi_none.csv
    [..]
    user_import.delete_users:441  ------ Deleting 1 users... ------
    [..]
    sisopi_user_import.do_delete:195  Removing ImportStudent(name='peter.silie1', school='DEMOSCHOOL', dn='uid=peter.silie1,cn=schueler,cn=users,ou=DEMOSCHOOL,dc=uni,dc=dtr') from school 'DEMOSCHOOL'...
    sisopi_user_import.do_delete:211  Moving ImportStudent(name='peter.silie1', school='DEMOSCHOOL', dn='uid=peter.silie1,cn=schueler,cn=users,ou=DEMOSCHOOL,dc=uni,dc=dtr') to limbo school u'limbo'.
    [..]
    user_import.log_stats:742  Deleted ImportStudent: 1
    user_import.log_stats:742    ['peter.silie1']

    udm users/user list --filter uid=peter.silie1 | egrep 'DN|school:|group'
    DN: uid=peter.silie1,cn=schueler,cn=users,ou=limbo,dc=uni,dc=dtr
    groups: cn=Domain Users limbo,cn=groups,ou=limbo,dc=uni,dc=dtr
    groups: cn=schueler-limbo,cn=groups,ou=limbo,dc=uni,dc=dtr
    primaryGroup: cn=Domain Users limbo,cn=groups,ou=limbo,dc=uni,dc=dtr
    school: limbo
    ucsschoolRole: student:school:limbo

Test: create in two schools, delete in one
------------------------------------------
Create another OU ``SchuleEins``::

    /usr/share/ucs-school-import/scripts/create_ou SchuleEins

First reset the unique username counter::

    /usr/share/ucs-school-import/scripts/reset_schema_counter --username -p peter.silie -w

To import a user into two schools, two imports must run::

    /usr/share/ucs-school-import/scripts/ucs-school-user-import -v -s DEMOSCHOOL -i /tmp/sisopi1.csv
    /usr/share/ucs-school-import/scripts/ucs-school-user-import -v -s SchuleEins -i /tmp/sisopi1.csv

The user will be in two schools now and one school class per school::

    udm users/user list --filter uid=peter.silie1 | egrep 'DN|school:|group'
    DN: uid=peter.silie1,cn=schueler,cn=users,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=Domain Users SchuleEins,cn=groups,ou=SchuleEins,dc=uni,dc=dtr
    groups: cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=schueler-schuleeins,cn=groups,ou=SchuleEins,dc=uni,dc=dtr
    groups: cn=DEMOSCHOOL-igel,cn=klassen,cn=schueler,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=SchuleEins-igel,cn=klassen,cn=schueler,cn=groups,ou=SchuleEins,dc=uni,dc=dtr
    primaryGroup: cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    school: DEMOSCHOOL
    school: SchuleEins
    ucsschoolRole: student:school:DEMOSCHOOL
    ucsschoolRole: student:school:SchuleEins

To remove the user from one school, import the empty CSV file for *that* school::

    /usr/share/ucs-school-import/scripts/ucs-school-user-import -v -s SchuleEins -i /tmp/sisopi_none.csv

The user is then removed from that school and that schools school classes::

    udm users/user list --filter uid=peter.silie1 | egrep 'DN|school:|group'
    DN: uid=peter.silie1,cn=schueler,cn=users,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=schueler-demoschool,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    groups: cn=DEMOSCHOOL-igel,cn=klassen,cn=schueler,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    primaryGroup: cn=Domain Users DEMOSCHOOL,cn=groups,ou=DEMOSCHOOL,dc=uni,dc=dtr
    school: DEMOSCHOOL
    ucsschoolRole: student:school:DEMOSCHOOL

If that school would have been the primary school, the user object would have been moved to the alphabetically first school of the remaining schools.
