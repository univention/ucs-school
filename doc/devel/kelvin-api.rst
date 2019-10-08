.. to compile run:
..     $ rst2html5 kelvin-api.rst kelvin-api.html

Kelvin API
==========

Building
--------

The Kelvin API will be delivered as a UCS app within a Docker container. To build the container run::

	$ cd kelvin-api
	$ make build-docker-image

Pushing image to Docker registry
--------------------------------

To push the Docker image to Univentions Docker registry, the image has to be built on the host ``docker.knut.univention.de``::

	$ ssh root@docker.knut.univention.de
	# list existing images
	$ docker images docker-test-upload.software-univention.de/ucsschool-kelvin
	# update ucsschool repo (branch dtroeder/ucsschool.no.udm)
	$ cd ucsschool-kelvin/ucsschool
	$ git pull

Optionally sync not yet commited changes from your local git repo to the server::

	$ cd $UCSSCHOOL-GIT
	$ git checkout dtroeder/ucsschool.no.udm
	$ rsync -avn --delete --exclude --exclude .git --exclude docker/build --exclude docker/ucs ./ root@docker.knut.univention.de:ucsschool-kelvin/ucsschool/
	# check output, changes should be only recent commits and your changes
	# if OK: remove '-n' from rsync cmdline

Build image on the ``docker`` host and push it to the Docker registry::

	$ ssh root@docker.knut.univention.de
	$ cd ucsschool-kelvin/ucsschool/docker
	$ git pull
	$ ./build_docker_image --push

If the build suceeds, you'll be asked::

	Push 'Y' if you are sure you want to push 'docker-test-upload.software-univention.de/ucsschool-kelvin:0.1.0-test' to the docker registry.

Type (upper case) ``Y`` to start the push.


Tests
-----

Tests are run during Docker image built. To run them manually during development::

	$ . ~/virtenvs/schoollib/bin/activate
	$ cd kelvin-api
	$ make test

Code style
----------

Code style is checked during Docker image built. To check it manually during development::

	$ . ~/virtenvs/schoollib/bin/activate
	$ cd kelvin-api
	$ make lint

If a check related to PEP8 fails, run::

	$ . ~/virtenvs/schoollib/bin/activate
	$ cd kelvin-api
	$ make format

Coverage
--------

Code coverage is checked during every ``pytest`` run, so also during Docker image build. To start it manually read chapter `Tests`.

Installation on developer PC
----------------------------

The ucs-school-lib Python package and all its dependencies are required. See `ucsschool_lib_with_remote_UDM.rst <ucsschool_lib_with_remote_UDM.rst>`_.

Install the kelvin-api package::

	$ . ~/virtenvs/schoollib/bin/activate
	$ cd $UCSSCHOOL-GIT/kelvin-api
	$ make install

Create directory for log file::

	$ sudo mkdir -p /var/log/univention/ucs-school-kelvin/
	$ sudo chown $USER /var/log/univention/ucs-school-kelvin/

Make sure UCR is setup::

	$ for ucrv in ldap/base ldap/server/name ldap/hostdn ldap/server/port; do grep $ucrv /etc/univention/base.conf || echo "Error: missing $ucrv" || break; done

Create admin group on the UCS@school host::

	$ udm groups/group create --ignore_exists \
		--position "cn=groups,$(ucr get ldap/base)" \
		--set name="ucsschool-kelvin-admins" \
		--set description="Users that are allowed to connect to the Kelvin API." \
		--append "users=uid=Administrator,cn=users,$(ucr get ldap/base)"

Create secret key file for token signing::

	$ sudo mkdir -p /var/lib/univention-appcenter/apps/ucs-school-kelvin-api/conf/
	$ sudo chown $USER /var/lib/univention-appcenter/apps/ucs-school-kelvin-api/conf/
	$ openssl rand -hex 32 > /var/lib/univention-appcenter/apps/ucsschool-kelvin/conf/tokens.secret

Running it on developer PC
--------------------------

No Apache configuration yet, for now just start the ASGI server directly::

	$ uvicorn ucsschool.kelvin.main:app --reload

Then open http://127.0.0.1:8000/kelvin/api/v1/docs in your browser.

...

TODOs
-----

Change signatures back to using ``name`` (instead of ``username`` and ``class_name``), when https://github.com/encode/starlette/pull/611 has been merged.
