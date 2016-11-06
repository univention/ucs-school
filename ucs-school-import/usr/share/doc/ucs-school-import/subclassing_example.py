#
# This is an example of how advanced modifications can be made to the import
# code.
#
# 1. Subclass the classes whose code need modification.
# 2. Tell the default factory to use your class instead of the standard class.
#
#    See user_import_configuration_readme.txt for a list of classes that can be
#    replaced like this. Below is an example of how to change the configuration
#    and for a subclass.
#
#    The DefaultUserImportFactory code can be found in
#    /usr/share/pyshared/ucsschool/importer/default_user_import_factory.py
#

#
# Store your class (in the example it is _this_ file) somewhere it is found
# by the system Python installation:
# mkdir -p /usr/local/lib/python2.7/dist-packages
# cp /usr/share/doc/ucs-school-import/subclassing_example.py /usr/local/lib/python2.7/dist-packages
#
# Test with:
# python -c 'from subclassing_example import MyUserImport'
# (Output should be none - at least no ImportError.)
#
# Then change the configuration like this:
# (Replace "/var/lib/ucs-school-import/configs/myconfig.json" with your actual
# configuration file and "subclassing_example.MyUserImport" with your module.class.)
#
# python -c 'MYCFG="/var/lib/ucs-school-import/configs/myconfig.json"; import json; cnf=json.load(open(MYCFG, "rb")); cnf["classes"]=cnf.get("classes", {}); cnf["classes"]["user_importer"]="subclassing_example.MyUserImport"; json.dump(cnf, open(MYCFG+".new", "wb"), indent=4)'
#
# Verfiy that /var/lib/ucs-school-import/configs/myconfig.json.new is correct and replace
# /var/lib/ucs-school-import/configs/myconfig.json with it.
#
# The next import run should use the MyUserImport class instead of the
# UserImport class and you should see a line in the logfile directly below the
# configuration dump:
#
# INFO  DefaultUserImportFactory.make_user_importer is now <class 'subclassing_example.MyUserImport'>.
#

import datetime
from ucsschool.importer.mass_import.user_import import UserImport


class MyUserImport(UserImport):

	def do_delete(self, user):
		"""
		Delete or deactivate a user.
		IMPLEMENTME to add or change a deletion variant.

		:param user: ImportUser
		:return bool: whether the deletion worked
		"""
		if user.birthday == datetime.datetime.now().strftime("%Y-%m-%d"):
			self.logger.info("Not deleting user %s on its birthday!", user)
			return True
		else:
			return super(MyUserImport, self).do_delete(user)
