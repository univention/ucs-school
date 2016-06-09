User import configuration file reference
========================================

Configuration files are interpreted in a hierarchical way.
*Please read global_configuration_readme.txt first!*

After reading the global configuration options (1. and 2.), module specific
configuration is read. In case of the user import, those are:

3. /usr/share/ucs-school-import/configs/user_import_defaults.json (do not edit)
4. /var/lib/ucs-school-import/configs/user_import.json (edit this)

After that follow
5. Configuration file set on the command line.
6. Options set on the command line by --set and its aliases.


[1]: mandatory
[2]: default value for [3]
[3]: if this is not set, fall back to [2]


"factory": str: fully dotted path to (a subclass of) ucsschool.importer.default_user_import_factory.DefaultUserImportFactory
"classes": {
	"reader": str: fully dotted path to a subclass of BaseReader e.g. "ucsschool.importer.reader.csv_reader.CsvReader"
	"import_user":  str: fully dotted path to a *function* that returns an object of the appropriate subclass of ImportUser
	"mass_importer":  str: fully dotted path to a subclass of ucsschool.importer.mass_import.mass_import.MassImport
	"password_exporter":  str: fully dotted path to a subclass of ucsschool.importer.writer.result_exporter.ResultExporter
	"result_exporter":  str: fully dotted path to a subclass of ucsschool.importer.writer.result_exporter.ResultExporter
	"user_importer":  str: fully dotted path to a subclass of ucsschool.importer.mass_import.user_import.UserImport
	"username_handler":  str: fully dotted path to a subclass of ucsschool.importer.utils.username_handler.UsernameHandler
	"user_writer":  str: fully dotted path to a subclass of ucsschool.importer.writer.base_writer.BaseWriter
},
"input": {
	"type": str [1]: "csv", "json", "socket" etc
	"filename": str: path to the input file (csv etc)
},
"activate_new_users": {
	"default":           bool [2]: if the new user should be activated
	"student":           bool [3]: if the new user should be activated
	"staff":             bool [3]: if the new user should be activated
	"teacher":           bool [3]: if the new user should be activated
	"teacher_and_staff": bool [3]: if the new user should be activated
},
"csv": {
	"delimiter": str: character that separates the cells of two columns (defaults to ',')
	"header_lines": int: how many line to skip, if 1, first line will be used to create keys for dict
	"incell-delimiter": {
		"default":               str [2]: multi-value field separator symbol, separates two values inside a cell
    	<udm attribute name>:    str [3]:                (not between columns like "delimiter", defaults to ',')
	}
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
	},
	<udm attribute name>:	str: scheme (manual-4.1:users:templates) to create a UDM attribute from
},
"maildomain": str: value of 'maildomain' variable that can be used in scheme->email. If unset will try to find one in system.
"mandatory_attributes": list: list of UDM attribute names that must be set by the import
"no_delete": bool: if set to True, users missing in the input will not be deleted in LDAP.
"outdated_users": {
	"delete": bool:
	"deactivate": bool:
	"waiting_period": int:
},
"output": {
	"new_user_passwords": str: path to the new users passwords file
	"user_import_summary": str: path to a file to write the summary in CSV fomat to
},
"password_length": int [1]: length of the random password generated for new users
"school": str: name (abbreviation) of school this import is for, if not available from input
"sourceUID": str [1]: UID of source database
"tolerate_errors": int [1]: number of non-fatal UcsSchoolImportErrors to tolerate before aborting
"user_deletion": {
	"delete":	bool: if the user should be deleted (false -> it will be deactivated)
	"expiration": int: number of days before the account will be deleted or deactivated
},
"user_role": str: if set, all new users from input will have that role (student|staff|teacher|teacher_and_staff)
