# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

#
# # IMPORTANT
#
# After a rebuild, update the pinned digest in IMAGE_BASEDPYRIGHT_UCS
# (.gitlab-ci/gitlab-ci.yml) and the basedpyright-container-* hooks
# (.pre-commit-config.yaml), e.g. via `docker buildx imagetools inspect`.
# and refresh the baseline (`./basedpyright-baseline.json`)!

ARG UCS_VERSION=526
ARG UCS_BASE_IMAGE_TAG=latest

# Used only as a source for the dev-branch apt key + helper script (see
# UCS_DEV_BRANCH below) - ucs-base-python-* doesn't ship these, ucs-base-dev-*
# does.
FROM gitregistry.knut.univention.de/univention/dev/projects/ucs-base-image/ucs-base-dev-${UCS_VERSION}:${UCS_BASE_IMAGE_TAG} AS ucs-dev-branch-tools

FROM gitregistry.knut.univention.de/univention/dev/projects/ucs-base-image/ucs-base-python-${UCS_VERSION}:${UCS_BASE_IMAGE_TAG}

# Optional: build against an in-development branch of the `ucs` repo instead
# of the released errata channel, mirroring ucs-base-image's own
# dev.Dockerfile.usage-example. Leave empty (default) to use only the
# released/errata index already baked into the base image - matching
# ucs-base-image's reproducibility guidance below, we skip "apt-get update"
# in that case.
#
# If set (e.g. --build-arg UCS_DEV_BRANCH=5-2-2), a git branch named
# "your/branch" becomes slug "your-branch" here; find the generated slug in
# the output of the pipeline job that built the debian package for that
# branch.
ARG UCS_DEV_BRANCH=""

COPY --from=ucs-dev-branch-tools /etc/apt/trusted.gpg.d/development-key-omar.gpg /etc/apt/trusted.gpg.d/development-key-omar.gpg
COPY --from=ucs-dev-branch-tools /usr/local/bin/ucs-dev-add-branch.sh /usr/local/bin/ucs-dev-add-branch.sh

# Note: without UCS_DEV_BRANCH, the packages index is already included in the
# base image. Running "apt-get update" in that case would pull in newer
# errata and make this image non-reproducible against a rolling errata
# channel, so we only do it when a dev branch was actually added.
#
# Some UCS postinsts start daemons inside the build container - for example
# univention-nagios-client runs "/etc/init.d/nagios-nrpe-server restart"
# directly, bypassing invoke-rc.d and therefore policy-rc.d. A daemon that
# outlives this RUN keeps the container's cgroup populated, and buildkit-runc
# then aborts the build with "unable to remove container's cgroup: device or
# resource busy", after apt-get has already finished successfully. The sweep at
# the end of the layer kills whatever is left over.
#
# The sweep must not kill anything but our own leftovers: the buildkit CI
# component runs the rootless image with --oci-worker-no-process-sandbox, so
# this RUN shares the job container's PID namespace and sees buildkitd and the
# runner itself. Our processes are the ones whose /proc/<pid>/root resolves to
# this container's root filesystem, which is what the marker file below tests -
# a process we cannot inspect at all is left alone.
# hadolint ignore=DL3008
RUN if [ -n "$UCS_DEV_BRANCH" ]; then \
      ucs-dev-add-branch.sh "$UCS_DEV_BRANCH" && apt-get update; \
    fi \
    && apt-get install --assume-yes --verbose-versions --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/* \
    && marker=/.build-daemon-sweep \
    && : > "$marker" \
    && for proc in /proc/[0-9]*; do \
         pid="${proc#/proc/}"; \
         { [ "$pid" = "$$" ] || [ "$pid" = 1 ]; } && continue; \
         [ -e "$proc/root$marker" ] && kill -9 "$pid" 2>/dev/null; \
         :; \
       done \
    && rm -f "$marker" \
    && sleep 1

COPY requirements-typecheck.txt /tmp/requirements-typecheck.txt

# uv and prek are installed into this same --system-site-packages venv so the image can
# serve both the python-type-hint-coverage-basedpyright CI component and the run_pre_commit
# job (see .gitlab-ci/gitlab-ci.yml).
RUN python3 -m venv --system-site-packages /opt/basedpyright-venv \
    && /opt/basedpyright-venv/bin/pip install --no-cache-dir \
         "basedpyright==1.39.8" uv prek -r /tmp/requirements-typecheck.txt \
    && rm /tmp/requirements-typecheck.txt \
    && ln -s /opt/basedpyright-venv/bin/uv /usr/local/bin/uv \
    && ln -s /opt/basedpyright-venv/bin/uvx /usr/local/bin/uvx \
    && ln -s /opt/basedpyright-venv/bin/prek /usr/local/bin/prek \
    && ln -s /opt/basedpyright-venv/bin/basedpyright /usr/local/bin/basedpyright
