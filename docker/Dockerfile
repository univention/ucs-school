# Copyright 2020-2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

FROM alpine:3.12

ARG app_id
ARG commit
ARG date
ARG version

VOLUME /var/log

WORKDIR /kelvin

EXPOSE 7890

CMD ["/sbin/init"]

LABEL "description"="Image of UCS app 'UCS@school Kelvin REST API' ('$app_id')." \
    "url"="https://www.univention.com/products/univention-app-center/app-catalog/$app_id/" \
    "version"="$version" \
    "release date"="$date" \
    "commit"="$commit"

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
    python3 -m venv --system-site-packages /kelvin/venv && \
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile --upgrade pip wheel && \
	# build ujson from source https://github.com/esnme/ultrajson/issues/326
	/kelvin/venv/bin/python3 -m pip install git+git://github.com/esnme/ultrajson.git@2.0.3 && \
	# Install already, since it would fetch old versions from test.pypi.org in a later step.
	/kelvin/venv/bin/python3 -m pip install aiohttp certifi && \
	# python-debian for UCR
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile python-debian && \
	# install pre-build openapi-client-udm package, not yet built against app host
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile -i https://test.pypi.org/simple/ openapi-client-udm && \
	# install most current udm_rest_client package (instead of the one from pypi)
	/kelvin/venv/bin/python3 -m pip install git+git://github.com/univention/python-udm-rest-api-client.git && \
	# install all remaining Python requirements
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile -r /tmp/requirements_all.txt && \
    apk del --no-cache \
        g++ \
        gcc \
        git \
        musl-dev \
        python3-dev \
        linux-headers && \
	rm -rf /tmp/*

# install univention libraries
COPY univention-lib-slim/ /tmp/univention-lib-slim
COPY univention-directory-manager-modules-slim/ /tmp/univention-directory-manager-modules-slim
RUN /kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile -i https://test.pypi.org/simple/ univention-config-registry && \
    ln -sv /usr/bin/univention-config-registry /usr/bin/ucr && \
    mkdir -p /etc/univention && \
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile /tmp/univention-lib-slim && \
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --compile /tmp/univention-directory-manager-modules-slim && \
	rm -rf /tmp/*

# copy and install project - separate last step for fast image rebuilds
# install packages 'editable', so we can work directly on them
COPY ucs-school-lib/ /kelvin/ucs-school-lib
COPY ucs-school-import/ /kelvin/ucs-school-import
COPY ucsschool-kelvin-rest-api.initd /tmp/
COPY kelvin-api/ /kelvin/kelvin-api
RUN	mv -v /tmp/ucsschool-kelvin-rest-api.initd /etc/init.d/ucsschool-kelvin-rest-api && \
	rc-update add ucsschool-kelvin-rest-api default && \
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --editable /kelvin/ucs-school-lib/modules && \
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --editable /kelvin/ucs-school-import/modules && \
	cp -r /kelvin/ucs-school-import/usr/share/ucs-school-import /usr/share/ && \
	cp kelvin-api/usr/share/ucs-school-import/configs/kelvin_defaults.json /usr/share/ucs-school-import/configs/ && \
	cp kelvin-api/usr/share/ucs-school-import/checks/*.py /usr/share/ucs-school-import/checks/ && \
	mkdir -p /usr/share/ucs-school-import/pyhooks && \
	mkdir -p /var/lib/ucs-school-import && \
	cp -r /kelvin/ucs-school-import/empty_configs /var/lib/ucs-school-import/configs && \
	/kelvin/venv/bin/python3 /kelvin/kelvin-api/setup.py build_html && \
	/kelvin/venv/bin/python3 -m pip install --no-cache-dir --editable /kelvin/kelvin-api[development] && \
	source /kelvin/venv/bin/activate && \
	(cd /kelvin/ucs-school-lib/modules && python -m pytest) && \
	make -C /kelvin/kelvin-api lint && \
	make -C /kelvin/kelvin-api test && \
	make -C /kelvin/kelvin-api clean && \
	find /kelvin -name .pytest_cache -exec rm -rf '{}' + && \
	rm -rf /root/.cache/
