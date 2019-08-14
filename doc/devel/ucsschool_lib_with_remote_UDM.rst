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

Current development state / how to install
------------------------------------------

Development can be done on any Linux distro using virtualenv::

	$ virtualenv -p python3.7 ~/virtenvs/schoollib
	$ . ~/dev/virtenvs/schoollib/bin/activate

	$ cd $UCS-REPO
	$ git checkout dtroeder/ucr.pip.installable
	$ pip install base/univention-config-registry/python/

	$ cd $UCSSCHOOL-REPO
	$ git checkout dtroeder/ucsschool.no.udm
	$ pip install -e ucs-school-lib/modules/

Test installation::

	$ sudo touch /etc/univention/base.conf
	$ sudo chown $USER /etc/univention/base*
	$ sudo mkdir -p /var/cache/univention-config
	$ sudo chown $USER /var/cache/univention-config

	$ python -c 'from univention.config_registry import handler_set; handler_set(["foo=bar"])'
	# nothing happens to base.conf -> handler_set() does not work yet :(
	# so fake it for now:
	$ echo -en "\nfoo: bar" >> /etc/univention/base.conf

	$ python -c 'from ucsschool.lib.models.utils import ucr; assert ucr.get("foo") == "bar"'
