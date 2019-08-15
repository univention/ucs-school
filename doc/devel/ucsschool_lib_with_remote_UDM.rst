.. to compile run: rst2html5 ucsschool_lib_with_remote_UDM.rst ucsschool_lib_with_remote_UDM.html

ucsschool.lib with remote UDM
==============================

Goals
-----

* The ``ucsschool.lib`` package can be used on any Linux distro.
* The ``ucsschool.lib`` package can be installed using Python ``setuptools``.

Consequences and constraints
----------------------------

* Modules in the ``ucsschool.lib`` package can be used without a local installation of UDM.
* UDMs HTTP-API interface is used to make modifications to LDAP.
* Direct LDAP access is allowed, but cannot use the ``uldap`` module.

Installation
------------

The following libs have to be installed:
    python3.7
    python3.7-dev
    libldap2-dev
    libsasl2-dev

Development can be done on any Linux distro using virtualenv::

	$ virtualenv -p python3.7 ~/virtenvs/schoollib
	$ . ~/dev/virtenvs/schoollib/bin/activate

	$ cd $UCS-REPO
	$ git checkout dtroeder/ucr.pip.installable
	$ pip install base/univention-config-registry/python/

	$ cd $UCSSCHOOL-REPO
	$ git checkout dtroeder/ucsschool.no.udm
	$ pip install univention-lib-slim
	$ pip install univention-directory-manager-modules-slim
	$ pip install -e ucs-school-lib/modules

Test UCR installation::

	$ sudo touch /etc/univention/base.conf
	$ sudo chown $USER /etc/univention/
	$ sudo mkdir -p /var/cache/univention-config
	$ sudo chown $USER /var/cache/univention-config

	$ python -c 'from univention.config_registry import handler_set; handler_set(["foo=bar"])'
	# nothing happens to base.conf -> handler_set() does not work yet :(
	# so fake it for now:
	$ echo -en "\nfoo: bar" >> /etc/univention/base.conf

	$ python -c 'from ucsschool.lib.models.utils import ucr; assert ucr.get("foo") == "bar"'

Test logging::

	$ python -c 'import logging; from ucsschool.lib.models.utils import get_file_handler, get_stream_handler; logger = logging.getLogger("foo"); logger.setLevel("DEBUG"); logger.addHandler(get_file_handler("DEBUG", "/tmp/log")); logger.addHandler(get_stream_handler("DEBUG")); logger.debug("debug msg"); logger.error("error msg")'
	$ cat /tmp/log


Store machine credentials (if not in app container)::

	import ruamel.yaml
	with open("/etc/univention/master.secret", "w") as fp:
		ruamel.yaml.dump({
			"uri": "http://10.200.3.66/univention/udm/",
			"username": "Administrator",
			"password": "univention"},
			fp, ruamel.yaml.RoundTripDumper, indent=4
		)


Status
------

Import possible::

	ucsschool.lib.i18n
	ucsschool.lib.models
	ucsschool.lib.models.attributes
	ucsschool.lib.models.base
	ucsschool.lib.models.computer
	ucsschool.lib.models.dhcp
	ucsschool.lib.models.group
	ucsschool.lib.models.meta
	ucsschool.lib.models.misc
	ucsschool.lib.models.network
	ucsschool.lib.models.policy
	ucsschool.lib.models.school
	ucsschool.lib.models.share
	ucsschool.lib.models.user
	ucsschool.lib.models.utils
	ucsschool.lib.pyhooks
	ucsschool.lib.pyhooks.pyhook
	ucsschool.lib.pyhooks.pyhooks_loader
	ucsschool.lib.roles
	ucsschool.lib.schoolldap
	ucsschool.lib.smbstatus

Import error::

	ucsschool.lib.info
	ucsschool.lib.internetrules
	ucsschool.lib.roleshares
	ucsschool.lib.school_umc_base
	ucsschool.lib.school_umc_ldap_connection
	ucsschool.lib.schoollessons

Code execution tested::

	ucsschool.lib.models.utils.*
	ucsschool.lib.models.computer.AnyComputer.get_all
	ucsschool.lib.models.groups.SchoolClass.get_all
	ucsschool.lib.models.user.User.get_all
