# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from django_pam.auth.backends import PAMBackend


class UASImportPAMBackend(PAMBackend):
    """Purpose: Make `uas-import` the default PAM service instead of `login`"""

    def authenticate(self, request, username=None, password=None, **extra_fields):
        service = extra_fields.pop("service", "uas-import")
        extra_fields.update({"service": service})
        return super().authenticate(request, username, password, **extra_fields)
