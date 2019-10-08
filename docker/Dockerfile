#
# Dockerfile optimized for fast image rebuilds
#

FROM alpine:edge

ARG version

VOLUME /var/log

LABEL "description"="UCS@school Kelvin-API" \
    "version"="$version"

WORKDIR /kelvin

EXPOSE 7890

CMD ["/sbin/init"]

# package and Python dependency installation, base system configuration,
# and uninstallation - all in one step to keep image small
COPY requirements_all.txt /tmp/
RUN echo '@testing http://dl-cdn.alpinelinux.org/alpine/edge/testing' >> /etc/apk/repositories && \
    apk add --no-cache \
        busybox-initscripts \
        gcc \
        make \
        musl-dev \
        openldap-dev \
        openrc \
        python3 \
        python3-dev \
        py3-aiohttp \
        py3-attrs \
        py3-colorlog@testing \
        py3-docutils \
        py3-flake8 \
        py3-isort \
        py3-jwt \
        py3-lazy-object-proxy@testing \
        py3-ldap3 \
        py3-msgpack \
        py3-packaging \
        py3-pytest \
        py3-pytest-runner \
        py3-requests \
        py3-setproctitle \
        py3-simplejson \
        py3-ujson@testing \
        py3-yarl \
        tzdata && \
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
    python3.7 -m venv --system-site-packages /kelvin/venv && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile --upgrade pip && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile black python-debian && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile -r /tmp/requirements_all.txt && \
    apk del --no-cache \
        gcc \
        musl-dev \
        python3-dev && \
	rm -rf /tmp/*

# install univention libraries
COPY univention-config-registry/ /tmp/univention-config-registry
COPY univention-lib-slim/ /tmp/univention-lib-slim
COPY univention-directory-manager-modules-slim/ /tmp/univention-directory-manager-modules-slim
RUN /kelvin/venv/bin/pip3 install --no-cache-dir --upgrade --compile pip && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile /tmp/univention-config-registry/python && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile /tmp/univention-lib-slim && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --compile /tmp/univention-directory-manager-modules-slim && \
	rm -rf /tmp/*

# copy and install project - separate last step for fast image rebuilds
# install packages 'editable', so we can work directly on them
COPY ucs-school-lib/ /kelvin/ucs-school-lib
COPY kelvin-api.initd /tmp/
COPY kelvin-api/ /kelvin/kelvin-api
RUN	mv -v /tmp/kelvin-api.initd /etc/init.d/kelvin-api && \
	rc-update add kelvin-api default && \
	/kelvin/venv/bin/pip3 install --no-cache-dir --editable /kelvin/ucs-school-lib/modules && \
	/kelvin/venv/bin/python3 /kelvin/kelvin-api/setup.py build_html && \
    /kelvin/venv/bin/pip3 install --no-cache-dir --editable /kelvin/kelvin-api[development] && \
	source /kelvin/venv/bin/activate && \
	make -C /kelvin/kelvin-api lint && \
	make -C /kelvin/kelvin-api test && \
	make -C /kelvin/kelvin-api clean && \
	rm -rf /root/.cache/
