# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
ARG UCS_VERSION=526
ARG UCS_BASE_IMAGE_TAG=latest

FROM gitregistry.knut.univention.de/univention/dev/projects/ucs-base-image/ucs-base-python-${UCS_VERSION}:${UCS_BASE_IMAGE_TAG}

# Note: the packages index is already included in the base image. Running
# "apt-get update" here would pull in newer errata and make this image
# non-reproducible against a rolling errata channel, so we skip it.
# hadolint ignore=DL3008
RUN apt-get install --assume-yes --verbose-versions --no-install-recommends \
      python3-venv python3-pip \
      python3-univention-config-registry \
      python3-univention-directory-manager \
      python3-univention-lib \
      python3-univention-management-console \
      univention-management-console-module-diagnostic \
      python3-univention \
      python3-univention-debug \
      python3-univention-appcenter \
      univention-directory-listener \
      python3-ldap python3-samba python3-pam python3-passlib \
      ucs-test-framework \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-typecheck.txt /tmp/requirements-typecheck.txt
# uv is installed into the same venv for the python-type-hint-coverage-basedpyright
# CI component, which calls "uv venv"/"uv pip install"/"uv run" directly. Its
# "uv run" shadows PATH with its own isolated venv, so that job resolves UCS
# imports via basedpyright's own "--pythonpath /usr/bin/python3" flag instead
# of relying on this venv.
RUN python3 -m venv --system-site-packages /opt/basedpyright-venv \
    && /opt/basedpyright-venv/bin/pip install --no-cache-dir "basedpyright==1.39.8" uv -r /tmp/requirements-typecheck.txt \
    && rm /tmp/requirements-typecheck.txt \
    && ln -s /opt/basedpyright-venv/bin/uv /usr/local/bin/uv \
    && ln -s /opt/basedpyright-venv/bin/uvx /usr/local/bin/uvx
