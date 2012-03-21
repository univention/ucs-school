/* 
 * Samba LDB module univention_samaccountname_ldap_check
 *	sample LDB Module for checking samaccountname adds against
 *	external LDAP
 *
 * Copyright 2011-2012 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */

/* univention_samaccountname_ldap_check was derived from the tests/sample_module

   Unix SMB/CIFS implementation.
   Samba utility functions
   Copyright (C) Jelmer Vernooij <jelmer@samba.org> 2007

     ** NOTE! The following LGPL license applies to the ldb
     ** library. This does NOT imply that all of Samba is released
     ** under the LGPL
   
   This library is free software; you can redistribute it and/or
   modify it under the terms of the GNU Lesser General Public
   License as published by the Free Software Foundation; either
   version 3 of the License, or (at your option) any later version.

   This library is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   Lesser General Public License for more details.

   You should have received a copy of the GNU Lesser General Public
   License along with this library; if not, see <http://www.gnu.org/licenses/>.
*/

#include "ldb_module.h"
#include "ldap.h"
#include <univention/config.h>
#include <univention/ldap.h>
// #include <univention/debug.h>

univention_ldap_parameters_t	*lp;

static char* read_pwd_from_file(char *filename)
{
	FILE *fp;
	char line[1024];
	int len;

	if ((fp = fopen(filename, "r")) == NULL)
		return NULL;
	if (fgets(line, 1024, fp) == NULL)
		return NULL;

	len = strlen(line);
	if (line[len-1] == '\n')
		line[len-1] = '\0';

	return strdup(line);
}

int do_connection(struct ldb_context *ldb, univention_ldap_parameters_t *lp)
{
	LDAPMessage *res;
	struct  timeval timeout;
	int rc;

	timeout.tv_sec=10;
	timeout.tv_usec=0;

	if ( univention_ldap_open(lp) != 0 ) {
		return 1;
	}

	/* check if we are connected to an OpenLDAP
	if ( (rc = ldap_search_ext_s(lp->ld, lp->base, LDAP_SCOPE_BASE, "objectClass=univentionBase", NULL, 0, NULL, NULL, &timeout, 0, &res) ) != LDAP_SUCCESS ) {
		if ( rc == LDAP_NO_SUCH_OBJECT ) {
			ldb_debug(ldb, LDB_DEBUG_ERROR, ("Failed to find \"(objectClass=univentionBase)\" on LDAP server %s:%d"), lp->host, lp->port);
		} else {
			ldb_debug(ldb, LDB_DEBUG_ERROR, ("Failed to search for \"(objectClass=univentionBase)\" on LDAP server %s:%d with message %s"), lp->host, lp->port, ldap_err2string(rc));
		}
		return 1;
	}
	ldap_msgfree( res );
	*/

	return 0;
}



static int univention_samaccountname_ldap_check(struct ldb_module *module, struct ldb_request *req)
{
	struct ldb_message_element *attribute;
	struct ldb_context *ldb;
	char *ldap_filter;
	LDAPMessage *res = NULL;
	int rv = LDAP_SUCCESS;
	int ret = LDB_SUCCESS;
	ldb = ldb_module_get_ctx(module);
	ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: ldb_add\n"), ldb_module_get_ops(module)->name);

	attribute = ldb_msg_find_element(req->op.add.message, "sAMAccountName");
	if (attribute) {

		// maybe better use module->private_data ?
		lp = talloc_zero(module, univention_ldap_parameters_t);

		lp->host=univention_config_get_string("ldap/master");
		lp->base=univention_config_get_string("ldap/base");
		lp->binddn=univention_config_get_string("ldap/hostdn");
		lp->bindpw=read_pwd_from_file("/etc/machine.secret");
		char *port = univention_config_get_string("ldap/master/port");
		lp->port=atoi(port);
		free(port);
		lp->start_tls=2;
		lp->authmethod = LDAP_AUTH_SIMPLE;
		if (do_connection(ldb, lp) != 0) {
			ldb_debug(ldb, LDB_DEBUG_ERROR, ("cannot connect to ldap server %s\n"), lp->host);
			if ( lp->ld != NULL ) {
				ldap_unbind_ext(lp->ld, NULL, NULL);
				lp->ld = NULL;
			}
			free(lp->host);
			free(lp->base);
			free(lp->binddn);
			free(lp->bindpw);
			talloc_free(lp);

			return LDB_ERR_UNAVAILABLE;
		}

		int ldap_filter_length = 6 + attribute->values[0].length + 1;
		ldap_filter = malloc(ldap_filter_length);
		snprintf( ldap_filter, ldap_filter_length, "(uid=%s)", attribute->values[0].data);
		char * attrs[] = { "dn", NULL };
		rv = ldap_search_ext_s(lp->ld, lp->base, LDAP_SCOPE_SUBTREE, ldap_filter, attrs, 0,  NULL /*serverctrls*/, NULL /*clientctrls*/, NULL /*timeout*/, 0 /*sizelimit*/, &res);
		if ( rv != LDAP_SUCCESS ) {
			ldb_debug(ldb, LDB_DEBUG_ERROR, ("%s: ldb_add: LDAP error: %s\n"), ldb_module_get_ops(module)->name, ldap_err2string(rv));
			ret = LDB_ERR_UNAVAILABLE;
		} else {
			if ( ldap_count_entries(lp->ld, res ) != 0 ) {
				ldb_debug(ldb, LDB_DEBUG_ERROR, ("%s: ldb_add: account %s exists on host %s\n"), ldb_module_get_ops(module)->name, (const char *)attribute->values[0].data, lp->host);
				ret = LDB_ERR_ENTRY_ALREADY_EXISTS;
			} else {
				ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: ldb_add: account %s ok\n"), ldb_module_get_ops(module)->name, (const char *)attribute->values[0].data);
			}
		}

		if ( res != NULL ) {
			ldap_msgfree( res );
		}
		if ( lp != NULL ) {
			if ( lp->ld != NULL ) {
				ldap_unbind_ext(lp->ld, NULL, NULL);
				lp->ld = NULL;
			}
			free(lp->host);
			free(lp->base);
			free(lp->binddn);
			free(lp->bindpw);
			talloc_free(lp);
		}
	}

	if ( ret == LDB_SUCCESS ) {
		ret = ldb_next_request(module, req);
	}

	return ret;
}

static int univention_samaccountname_ldap_check_add(struct ldb_module *module, struct ldb_request *req)
{
	struct ldb_context *ldb;

	/* check if there's a permissive control */
	struct ldb_control *control;
	control = ldb_request_get_control(req, LDB_CONTROL_PERMISSIVE_MODIFY_OID);
	if (control != NULL) {
		/* found go on */
		// ldb = ldb_module_get_ctx(module);
		// ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: permissive ldb_add\n"), ldb_module_get_ops(module)->name);
		return ldb_next_request(module, req);
	}

	ldb = ldb_module_get_ctx(module);
	ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: ldb_add\n"), ldb_module_get_ops(module)->name);
	return univention_samaccountname_ldap_check(module, req);
}

static int univention_samaccountname_ldap_check_modify(struct ldb_module *module, struct ldb_request *req)
{
	struct ldb_context *ldb;

	/* check if there's a permissive control */
	struct ldb_control *control;
	control = ldb_request_get_control(req, LDB_CONTROL_PERMISSIVE_MODIFY_OID);
	if (control != NULL) {
		/* found go on */
		// ldb = ldb_module_get_ctx(module);
		// ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: permissive ldb_modify\n"), ldb_module_get_ops(module)->name);
		return ldb_next_request(module, req);
	}

	ldb = ldb_module_get_ctx(module);
	ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: ldb_modify\n"), ldb_module_get_ops(module)->name);
	return univention_samaccountname_ldap_check(module, req);
}

static int univention_samaccountname_ldap_check_init_context(struct ldb_module *module)
{
	struct ldb_context *ldb;
	int ret;
	ret = ldb_mod_register_control(module, LDB_CONTROL_PERMISSIVE_MODIFY_OID);
	if (ret != LDB_SUCCESS) {
		ldb = ldb_module_get_ctx(module);
		ldb_debug(ldb, LDB_DEBUG_WARNING,
			"%s: "
			"Unable to register control with rootdse!",
			ldb_module_get_ops(module)->name);
	}

	return ldb_next_init(module);
}

static struct ldb_module_ops ldb_univention_samaccountname_ldap_check_module_ops = {
	.name	= "univention_samaccountname_ldap_check",
	.add	= univention_samaccountname_ldap_check_add,
	.modify	= univention_samaccountname_ldap_check_modify,
	.init_context	= univention_samaccountname_ldap_check_init_context,
};

int ldb_univention_samaccountname_ldap_check_init(const char *version)
{
	LDB_MODULE_CHECK_VERSION(version);
	return ldb_register_module(&ldb_univention_samaccountname_ldap_check_module_ops);
}
