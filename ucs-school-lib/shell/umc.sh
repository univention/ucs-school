#!/bin/sh
# -*- coding: utf-8 -*-
#
# Univention Lib
#  shell function for creating UMC operation and acl objects
#
# SPDX-FileCopyrightText: 2011-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

. /usr/share/univention-lib/umc.sh

eval "$(ucr shell ldap/base)"

BIND_ARGS="$@"

ucs_school_policies_create () {
	# create default policies

	additional_policy="$1"

	for policyname in ucsschool-umc-teachers-default ucsschool-umc-admins-default default-umc-all $additional_policy ; do
		udm policies/umc create $BIND_ARGS --ignore_exists \
			--position "cn=UMC,cn=policies,$ldap_base" --set name="${policyname}"
		if [ $? != 0 ]; then exit 1; fi
	done
}

ucs_school_policies_append () {
	# append operation set to all policies

	operation_set="$1"; shift
	additional_policy="$1"
	for policyname in ucsschool-umc-teachers-default ucsschool-umc-admins-default default-umc-all $additional_policy ; do
		udm policies/umc modify $BIND_ARGS --ignore_exists \
			--dn "cn=${policyname},cn=UMC,cn=policies,$ldap_base" \
			--append "allow=cn=$operation_set,cn=operations,cn=UMC,cn=univention,$ldap_base"
		if [ $? != 0 ]; then exit 1; fi
	done
}
