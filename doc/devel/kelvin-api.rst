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
	$ docker images docker-test-upload.software-univention.de/ucsschool-kelvin-rest-api
	# update ucsschool repo (branch feature/kelvin)
	$ cd ucsschool-kelvin/ucsschool
	$ git pull

Optionally sync not yet commited changes from your local git repo to the server::

	$ cd $UCSSCHOOL-GIT
	$ git checkout feature/kelvin
	$ make -C kelvin-api clean
	$ rsync -avn --delete ./ root@docker.knut.univention.de:ucsschool-kelvin/ucsschool/ --exclude docker/build --exclude docker/ucs --exclude .idea/ --exclude .git --exclude doc --exclude 'italc*' --exclude '*-umc-*' --exclude .pytest_cache --exclude __pycache__  --exclude '*.egg-info' --exclude '*.eggs'
	# check output, changes should be only recent commits and your changes
	# if OK: remove '-n' from rsync cmdline

If you want to build a new version of the docker image do not forget to increase the version number in kelvin-api/ucsschool/__init__.py as well as adding a new entry to the changelog.rst.

Build image on the ``docker`` host and push it to the Docker registry::

	$ ssh root@docker.knut.univention.de
	$ cd ucsschool-kelvin/ucsschool/docker
	$ git pull
	$ ./build_docker_image --push

If the build succeeds, you'll be asked::

	Push 'Y' if you are sure you want to push 'docker-test-upload.software-univention.de/ucsschool-kelvin-rest-api:1.0.0' to the docker registry.

Type (upper case) ``Y`` to start the push.

In the App Provider Portal you can then create a new App version using the new image you just created.


Update (un)join script and settings of app
------------------------------------------

The app settings and the join and unjoin scripts are in a ``appcenter`` directory in the UCS\@school git repository. There is also a script ``push_config_to_appcenter`` that can be used to upload those files to the Univention App Provider Portal::

	$ cd $UCSSCHOOL-GIT
	$ git checkout feature/kelvin
	$ cd appcenter
	$ ./push_config_to_appcenter

*Hint:* To upload the files to the App Provider Portal you will be asked for your username and password. Create ``~/.univention-appcenter-user`` (containing your username for the App Provider Portal) and ``~/.univention-appcenter-pwd`` (with your users password) to skip the question.

Tests
-----

Unit tests are run during Docker image built.
Integration tests have to be run manually during development::

	$ . ~/virtenvs/schoollib/bin/activate
	$ cd kelvin-api
	$ make test

ucs-tests are in ``ucs-test-ucsschool/94_ucsschool-api-kelvin``.
They require at least the following import configuration in ``/var/lib/ucs-school-import/configs/user_import.json``::

	{
		"configuration_checks": [
			"defaults",
			"mapped_udm_properties"
		],
		"mapped_udm_properties": [
			"description",
			"gidNumber",
			"employeeType",
			"organisation",
			"phone",
			"title",
			"uidNumber"
		]
	}


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

Auto-reload of API server during development
--------------------------------------------

The API server can be configured to reload itself, whenever a referenced Python module is changed::

	$ univention-app shell ucsschool-kelvin-rest-api
	$ export DEV=1
	$ /etc/init.d/ucsschool-kelvin-rest-api restart

Installation on developer PC
----------------------------

The ucs-school-lib Python package and all its dependencies are required. See `ucsschool_lib_with_remote_UDM.rst <ucsschool_lib_with_remote_UDM.rst>`_.

Install the kelvin-api package::

	$ . ~/virtenvs/schoollib/bin/activate
	$ cd $UCSSCHOOL-GIT/kelvin-api
	$ make install

Running it on developer PC
--------------------------

The ASGI server can be started directly. For the API to actually work a few environment variables need to be setup and a few files are required to be copied from a working app installation.

First get the root path of the Kelvin container and a few environment values::

	$ ssh <UCS-HOST>
	$ docker inspect --format='{{.GraphDriver.Data.MergedDir}}' "$(ucr get appcenter/apps/ucsschool-kelvin-rest-api/container)"
	# -> /var/lib/docker/overlay/41d1f8...3a520efa8/merged
	$ univention-app shell ucsschool-kelvin-rest-api ash -c "set | grep LDAP_"
	# -> LDAP_BASE='dc=uni,dc=dtr'
	# -> LDAP_HOSTDN='cn=ucssc-67054494,cn=memberserver,cn=computers,dc=uni,dc=dtr'
	# -> LDAP_MASTER='m150.uni.dtr'
	# ...

Then create and fill the ``dev`` directory with file required by the Kelvin API server::

	$ cd $UCSSCHOOL-GIT/kelvin-api
	$ mkdir -p \
		dev/etc/univention \
		dev/usr/local/share/ca-certificates \
		dev/usr/share/ucs-school-import/checks \
		dev/var/lib/ucs-school-import/configs \
		dev/var/lib/ucs-school-import/kelvin-hooks \
		dev/var/lib/univention-appcenter/apps/ucsschool-kelvin-rest-api/conf \
		dev/var/log/univention/ucsschool-kelvin-rest-api
	$ scp <UCS-HOST>:/var/lib/docker/overlay/41d...fa8/merged/etc/machine.secret dev/etc/
	$ scp <UCS-HOST>:/etc/univention/base*.conf dev/etc/univention
	$ scp <UCS-HOST>:/usr/local/share/ca-certificates/ucsCA.crt dev/usr/local/share/ca-certificates/ucs.crt
	$ scp <UCS-HOST>:/var/lib/univention-appcenter/apps/ucsschool-kelvin-rest-api/conf/*.secret dev/var/lib/univention-appcenter/apps/ucsschool-kelvin-rest-api/conf/

Now the Kelvin API can be started... Almost: Until Bug #51154 has not been fixed, a few environment variables are required. ::

	$ export LDAP_BASE=dc=uni,dc=dtr
	$ export LDAP_MASTER=m150.uni.dtr
	$ export LDAP_HOSTDN=cn=ucssc-67054494,cn=memberserver,cn=computers,dc=uni,dc=dtr

The Kelvin API can now be started like this::

	$ uvicorn --host 0.0.0.0 --port 8911 ucsschool.kelvin.main:app

To have it reload automatically in case a Python module of the Kelvin API was changed, run instead::

	$ uvicorn --host 0.0.0.0 --port 8911 --reload ucsschool.kelvin.main:app

If you want it to reload also if a Python module in another directory was changed, run::

	$ uvicorn --host 0.0.0.0 --port 8911 --reload --reload-dir ../ucs-school-lib/ --reload-dir ../ucs-school-import/ --reload-dir ucsschool/kelvin/ ucsschool.kelvin.main:app

The OpenAPI frontend can be found at: http://127.0.0.1:8911/kelvin/api/v1/docs

When the Kelvin API is running locally, the tests require the address::

	$ export DOCKER_HOST_NAME=127.0.0.1:8911
	$ python -m pytest -l -v tests/


TODOs
-----

Change signatures back to using ``name`` (instead of ``username`` and ``class_name``), when https://github.com/encode/starlette/pull/611 has been merged.
