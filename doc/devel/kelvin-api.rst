.. to compile run:
..     $ rst2html5 kelvin-api.rst kelvin-api.html

Kelvin API
==========

Installation
------------

The ucs-school-lib Python package and all its dependencies are required. See `ucsschool_lib_with_remote_UDM.rst <ucsschool_lib_with_remote_UDM.rst>`_.

Install the kelvin-api package::

	$ cd $UCSSCHOOL-GIT/kelvin-api
	$ python setup.py build_html
	$ pip3 install -e .

Create directory for log file::

	$ sudo mkdir -p /var/log/univention/kelvin-api/
	$ sudo chown $USER /var/log/univention/kelvin-api/

Make sure UCR is setup::

	$ for ucrv in ldap/base ldap/server/name ldap/hostdn ldap/server/port; do grep $ucrv /etc/univention/base.conf || echo "Error: missing $ucrv" || break; done

Create admin group on the UCS@school host::

	$ udm groups/group create --ignore_exists \
		--position "cn=groups,$(ucr get ldap/base)" \
		--set name="kelvin-users" \
		--set description="Users that are allowed to connect to the Kelvin API." \
		--append "users=uid=Administrator,cn=users,$(ucr get ldap/base)"

Create secret key file for token signing::

	$ sudo mkdir -p /var/lib/univention-appcenter/apps/ucs-school-kelvin-api/conf/
	$ sudo chown $USER /var/lib/univention-appcenter/apps/ucs-school-kelvin-api/conf/
	$ openssl rand -hex 32 > /var/lib/univention-appcenter/apps/ucs-school-kelvin-api/conf/tokens.secret

Running it
----------

No Apache configuration yet, for now just start the ASGI server directly::

	$ uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/kelvin/api/v1/docs in your browser.

Tests
-----

...

TODOs
-----

Change signatures back to using ``name`` (instead of ``username`` and ``class_name``), when https://github.com/encode/starlette/pull/611 has been merged.
