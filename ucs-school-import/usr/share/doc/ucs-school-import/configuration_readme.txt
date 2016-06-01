JSON configuration file reference
=================================

All options can be set from the command line using "--set <option>".

[1]: mandatory (probably much more than is marked)
[2]: default value for [3]
[3]: if this is not set, fall back to [2]


"factory": str: fully dotted path to (a subclass of) ucsschool.importer.default_factory.DefaultFactory
"input": {
	"type": str [1]: "csv", "json", "socket" etc
	"filename": str: path to the input file (csv etc)
}
"activate_new_users": {
	"default":           bool [2]: if the new user should be activated
	"student":           bool [3]: if the new user should be activated
	"staff":             bool [3]: if the new user should be activated
	"teacher":           bool [3]: if the new user should be activated
	"teacher_and_staff": bool [3]: if the new user should be activated
},
"csv": {
	"header_lines": int: how many line to skip, if 1, first line will be used to create keys for dict
		"mapping": {
			key: value -> str: str
			           -> 'value' must be either the name of an Attribute as supported by the ImportUser class
			              or it will used as a key in a dict 'udm_attribute'. Data from  'udm_attribute' will
			              be written to the underlying UDM object.
		}
},
"scheme" [1]: {
	"email": str: schema of email address, variables may be used as described in manual-4.1:users:templates
	"rid": str [1]: schema of RecordUID, variables may be used as described in manual-4.1:users:templates
	"username" [1]: {
		"allow_rename":      bool: whether changing usernames should be allowed (currently not supported,
		                           in the future may only work if scheme->rid does not contain the username)
		"default":           str [2]: schema of username, variables may be used
		"student":           str [3]:                     as described in manual-4.1:users:templates
		"staff":             str [3]:                     plus [COUNTER2] which is replaced by numbers
		"teacher":           str [3]:                     starting from 2 or [ALWAYSCOUNTER] which is
		"teacher_and_staff": str [3]:                     always replaced by numbers starting from 1.
	}
},
"csv_output":  str: path to the import job result file
"dry_run": bool: set to False if changes should be commited to LDAP
"logfile": str: path to additional logfile
"maildomain": str: value of 'maildomain' variable that can be used in scheme->email. If unset will try to find one in system.
"mandatory_attributes": list: list of UDM attribute names that must be set by the import
"no_delete": bool: if set to True, users missing in the input will not be deleted in LDAP.
"outdated_users": {
	"delete": bool:
	"deactivate": bool:
	"waiting_period": int:
},
"output": {
	"passwords": str: path to the new users passwords file
},
"password_length": int [1]: length of the random password generated for new users
"school": str: name (abbreviation) of school this import is for, if not available from input
"sourceUID": str [1]: UID of source database
"tolerate_errors": int [1]: number of non-fatal UcsSchoolImportErrors to tolerate before aborting
"user_deletion": {
	"delete":	bool: if the user should be deleted (false -> it will be deactivated)
	"expiration": int: number of days before the account will be deleted or deactivated
	}
"user_role": str: if set, all new users from input will have that role (student|staff|teacher|teacher_and_staff)
}
