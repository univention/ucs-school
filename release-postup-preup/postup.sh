#!/bin/bash

# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

phase="$1"
version="$2"

if [ "x$phase" = "xpost" ] && [ "x$version" = "x5.0-0" ]; then
	rm -f /etc/apt/preferences.d/99ucsschool500.pref
fi

exit 0
