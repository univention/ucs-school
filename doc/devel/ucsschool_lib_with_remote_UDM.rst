.. to compile run:
..     $ rst2html5 ucsschool_lib_with_remote_UDM.rst ucsschool_lib_with_remote_UDM.html

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

The following libs have to be installed on a Debian Buster system::

	$ apt install python3.7 python3.7-dev libldap2-dev libsasl2-dev virtualenv

When working on a UCS 4.4, install Python 3.7 from source::

	$ univention-install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev  libncursesw5-dev xz-utils tk-dev
	$ wget https://www.python.org/ftp/python/3.7.4/Python-3.7.4.tgz
	$ tar xzf Python-3.7.4.tgz
	$ cd Python-3.7.4
	$ ./configure --enable-optimizations --with-ensurepip=install
	$ make -j $(nproc)
	# zzz ~1h...
	$ make altinstall

LDAP and SASL libs are also needed::

	$ univention-install -y libldap2-dev libsasl2-dev

Development can be done on any Linux distro using ``virtualenv``::

	$ virtualenv -p python3.7 ~/virtenvs/schoollib
	$ . ~/virtenvs/schoollib/bin/activate

	$ cd $UCS-REPO
	$ git checkout dtroeder/ucr.pip.installable
	$ pip install base/univention-config-registry/python/

	$ cd $UCSSCHOOL-REPO
	$ git checkout dtroeder/ucsschool.no.udm
	$ pip install univention-lib-slim/
	# '/' at end is important, or pip will search pypi for "univention-lib-slim"
	$ pip install univention-directory-manager-modules-slim/
	$ pip install -e ucs-school-lib/modules

Setup UCR, *if not on UCS*::

	$ sudo touch /etc/univention/base.conf
	$ sudo chown -R $USER /etc/univention/
	$ sudo mkdir -p /var/cache/univention-config
	$ sudo chown $USER /var/cache/univention-config

Setup machine account, *if not on UCS* (would be done by appcenter when starting container)::

	# handler_set() does not work yet :(
	# so fake it for now with your test-VMs data:

	$ echo -en "\nldap/base: dc=uni,dc=dtr" >> /etc/univention/base.conf
	$ echo -en "\nldap/hostdn: cn=m150,cn=dc,cn=computers,dc=uni,dc=dtr" >> /etc/univention/base.conf
	$ echo -en "\nldap/server/name: m150.uni.dtr" >> /etc/univention/base.conf
	$ echo -en "\nldap/server/port: 7389" >> /etc/univention/base.conf

	$ echo -n "YBqavF9AnMxM" | sudo tee /etc/machine.secret

To overwrite the machine connection data in the current terminal::

	$ export ldap_base="dc=uni,dc=dtr"
	$ export ldap_hostdn="Administrator"
	$ export ldap_server_name="10.200.3.66"
	$ export ldap_machine_password="univention"

Test UDM HTTP API connection credentials::

	$ python -c 'from univention.admin.modules import get; print(get("users/user"))'

If you have connection problems, uncomment the ``print()`` statement in the ``get_machine_connection()`` function in ``univention-directory-manager-modules-slim/univention/admin/modules.py`` and rebuild the package with ``pip install univention-directory-manager-modules-slim/``.

Test logging::

	$ python -c 'import logging; from ucsschool.lib.models.utils import get_file_handler, get_stream_handler; logger = logging.getLogger("foo"); logger.setLevel("DEBUG"); logger.addHandler(get_file_handler("DEBUG", "/tmp/log")); logger.addHandler(get_stream_handler("DEBUG")); logger.debug("debug msg"); logger.error("error msg")'
	$ cat /tmp/log


Tests
-----
Automated tests are currently run from within the virtualenv. So they have no access to UDM. As they should use a different channel than the ucsschool.lib does (UDM HTTP-API), they issue commands via SSH. For that to work make sure your SSH key is stored without password on your UDM HTTP-API server, using the FQDN from UCR (``ldap/server/name``).

To run the tests, execute::

	$ cd $UCSSCHOOL-REPO/ucs-school-lib/modules
	$ python setup.py -v test
	# use "python -m pytest" for more control, e.g.:
	$ python -m pytest -l -s -v --lf

Once we have a UCS\@school HTTP-API, tests can be started from the UCS side.

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
	ucsschool.lib.models.groups.SchoolClass.create
	ucsschool.lib.models.groups.SchoolClass.get_all
	ucsschool.lib.models.groups.SchoolClass.modify
	ucsschool.lib.models.groups.SchoolClass.remove
	ucsschool.lib.models.user.User.create
	ucsschool.lib.models.user.User.get_all
	ucsschool.lib.models.user.User.modify
	ucsschool.lib.models.user.User.remove

