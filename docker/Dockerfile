FROM alpine:3.10

ARG version

VOLUME /var/log

WORKDIR /kelvin

EXPOSE 7890

CMD ["/sbin/init"]

LABEL "description"="UCS@school Kelvin-API" \
    "version"="$version"

# package and Python dependency installation, base system configuration,
# and uninstallation - all in one step to keep image small
COPY alpine_apk_list openapi-generator-cli-*.jar requirements_all.txt /tmp/
RUN apk add --no-cache $(cat /tmp/alpine_apk_list) && \
    cp -v /usr/share/zoneinfo/Europe/Berlin /etc/localtime && \
    echo "Europe/Berlin" > /etc/timezone && \
    # Disable getty's
    sed -i 's/^\(tty\d\:\:\)/#\1/g' /etc/inittab && \
    sed -i \
        # Change subsystem type to "docker"
        -e 's/#rc_sys=".*"/rc_sys="docker"/g' \
        # Allow all variables through
        -e 's/#rc_env_allow=".*"/rc_env_allow="\*"/g' \
        # Start crashed services
        -e 's/#rc_crashed_stop=.*/rc_crashed_stop=NO/g' \
        -e 's/#rc_crashed_start=.*/rc_crashed_start=YES/g' \
        # Define extra dependencies for services
        -e 's/#rc_provide=".*"/rc_provide="loopback net"/g' \
        /etc/rc.conf && \
    # Remove unnecessary services
    rm -fv /etc/init.d/hwdrivers \
        /etc/init.d/hwclock \
        /etc/init.d/modules \
        /etc/init.d/modules-load \
        /etc/init.d/modloop && \
    # Can't do cgroups
    sed -i 's/\tcgroup_add_service/\t#cgroup_add_service/g' /lib/rc/sh/openrc-run.sh && \
    sed -i 's/VSERVER/DOCKER/Ig' /lib/rc/sh/init.sh && \
    mkdir -pv /kelvin/openapi-generator/build /kelvin/openapi-generator/jar && \
    mv /tmp/openapi-generator-cli-*.jar /kelvin/openapi-generator/jar && \
    python3.7 -m venv --system-site-packages /kelvin/venv && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile --upgrade pip && \
	# build ujson from source https://github.com/esnme/ultrajson/issues/326
	/kelvin/venv/bin/pip3 install git+git://github.com/esnme/ultrajson.git && \
	# python-debian for UCR
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile python-debian && \
	# install pre-build openapi-client-udm package, not yet built against app host
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile -i https://test.pypi.org/simple/ openapi-client-udm && \
	# install most current udm_rest_client package (instead of the one from pypi)
	/kelvin/venv/bin/pip3 install git+git://github.com/univention/python-udm-rest-api-client.git && \
	# install all remaining Python requirements
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile -r /tmp/requirements_all.txt && \
    apk del --no-cache \
        g++ \
        gcc \
        git \
        musl-dev \
        python3-dev && \
	rm -rf /tmp/*

# install univention libraries
COPY univention-config-registry/ /tmp/univention-config-registry
COPY univention-lib-slim/ /tmp/univention-lib-slim
COPY univention-directory-manager-modules-slim/ /tmp/univention-directory-manager-modules-slim
RUN /kelvin/venv/bin/pip3 install --no-cache-dir --compile /tmp/univention-config-registry/python && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile /tmp/univention-lib-slim && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile /tmp/univention-directory-manager-modules-slim && \
	rm -rf /tmp/*

# copy and install project - separate last step for fast image rebuilds
# install packages 'editable', so we can work directly on them
COPY ucs-school-lib/ /kelvin/ucs-school-lib
COPY ucs-school-import/ /kelvin/ucs-school-import
COPY kelvin-api.initd /tmp/
COPY kelvin-api/ /kelvin/kelvin-api
RUN	mv -v /tmp/kelvin-api.initd /etc/init.d/kelvin-api && \
	rc-update add kelvin-api default && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --editable /kelvin/ucs-school-lib/modules && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --editable /kelvin/ucs-school-import/modules && \
	cp -r /kelvin/ucs-school-import/usr/share/ucs-school-import /usr/share/ && \
	cp kelvin-api/usr/share/ucs-school-import/configs/kelvin_defaults.json /usr/share/ucs-school-import/configs/ && \
	cp kelvin-api/usr/share/ucs-school-import/checks/*.py /usr/share/ucs-school-import/checks/ && \
	mkdir -p /usr/share/ucs-school-import/pyhooks && \
	mkdir -p /var/lib/ucs-school-import && \
	cp -r /kelvin/ucs-school-import/empty_configs /var/lib/ucs-school-import/configs && \
	/kelvin/venv/bin/python3 /kelvin/kelvin-api/setup.py build_html && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --editable /kelvin/kelvin-api[development] && \
	source /kelvin/venv/bin/activate && \
	(cd /kelvin/ucs-school-lib/modules && python -m pytest) && \
	make -C /kelvin/kelvin-api lint && \
	make -C /kelvin/kelvin-api test && \
	make -C /kelvin/kelvin-api clean && \
	find /kelvin -name .pytest_cache -exec rm -rf '{}' + && \
	rm -rf /root/.cache/
