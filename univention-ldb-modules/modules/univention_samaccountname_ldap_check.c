/* 
 * Samba LDB module univention_samaccountname_ldap_check
 *	LDB Module for checking samaccountname adds against external LDAP
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
#include <univention/config.h>
#include <stdbool.h>
#include "base64.h"
#include <unistd.h>
#include <string.h>
#include <sys/wait.h>

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

static int univention_samaccountname_ldap_check_add(struct ldb_module *module, struct ldb_request *req)
{
	struct ldb_context *ldb;
	struct ldb_message_element *attribute;
	bool is_computer = false;
	bool is_group = false;
	bool is_user = false;
	int i;

	/* check if there's a bypass_samaccountname_ldap_check control */
	struct ldb_control *control;
	control = ldb_request_get_control(req, LDB_CONTROL_BYPASS_SAMACCOUNTNAME_LDAP_CHECK_OID);
	if (control != NULL) {
		// ldb = ldb_module_get_ctx(module);
		// ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: plain ldb_add\n"), ldb_module_get_name(module));
		return ldb_next_request(module, req);
	}

	ldb = ldb_module_get_ctx(module);
	ldb_debug(ldb, LDB_DEBUG_TRACE, ("%s: ldb_add\n"), ldb_module_get_name(module));
	
	attribute = ldb_msg_find_element(req->op.add.message, "objectClass");
	for (i=0; i<attribute->num_values; i++) {
		if ( !(strcasecmp(attribute->values[i].data, "computer")) ) {
			is_computer = true;
		}
		if ( !(strcasecmp(attribute->values[i].data, "group")) ) {
			is_group = true;
		}
		if ( !(strcasecmp(attribute->values[i].data, "user")) ) {
			is_user = true;
		}
	}
			
	if ( is_computer ) {
		attribute = ldb_msg_find_element(req->op.add.message, "sAMAccountName");
		if( attribute == NULL ) {
			// we can't handle this
			return ldb_next_request(module, req);
		}
			
		char *new_computer_name = malloc(attribute->values[0].length);
		memcpy(new_computer_name, attribute->values[0].data, attribute->values[0].length - 1);
		new_computer_name[attribute->values[0].length] = 0;

		attribute = ldb_msg_find_element(req->op.add.message, "unicodePwd");
		if( attribute == NULL ) {
			// we can't handle this
			ldb_debug(ldb, LDB_DEBUG_ERROR, ("%s: ldb_add of computer object without unicodePwd\n"), ldb_module_get_name(module));
			return LDB_ERR_UNWILLING_TO_PERFORM;
		}

		char *unicodePwd_base64;
		size_t unicodePwd_base64_strlen = BASE64_ENCODE_LEN(attribute->values[0].length);
		unicodePwd_base64 = malloc(unicodePwd_base64_strlen + 1);
		base64_encode(*attribute->values[0].data, attribute->values[0].length, unicodePwd_base64, unicodePwd_base64_strlen + 1);
		char *opt_unicodePwd = malloc(11 + unicodePwd_base64_strlen + 1);
		sprintf(opt_unicodePwd, "unicodePwd=%s", unicodePwd_base64);
		opt_unicodePwd[11 + unicodePwd_base64_strlen] = 0;
		free(unicodePwd_base64);

		char *ldap_master = univention_config_get_string("ldap/master");
		char *machine_pass = read_pwd_from_file("/etc/machine.secret");
		char *my_hostname = univention_config_get_string("hostname");

		char *opt_name = malloc(5 + strlen(new_computer_name) + 1);
		sprintf(opt_name, "name=%s", new_computer_name);
		opt_name[5 + strlen(new_computer_name)] = 0;
		free(new_computer_name);

		int status;
		int pid=fork();
		if ( pid < 0 ) {

			ldb_debug(ldb, LDB_DEBUG_ERROR, ("%s: fork failed\n"), ldb_module_get_name(module));
			return LDB_ERR_UNWILLING_TO_PERFORM;

		} else if ( pid == 0 ) {

			execlp("/usr/sbin/umc-command", "/usr/sbin/umc-command", "-s", ldap_master, "-P", machine_pass, "-U", my_hostname, "selectiveudm/create_windows_computer", "-o", opt_name, "-o", opt_unicodePwd, NULL);

			ldb_debug(ldb, LDB_DEBUG_ERROR, ("%s: exec of /usr/sbin/umc-command failed\n"), ldb_module_get_name(module));
			_exit(1);
		} else {
			wait(&status);
			printf("child returned status %d\n", status);
		}

		free(ldap_master);
		free(machine_pass);
		free(my_hostname);
		free(opt_name);
		free(opt_unicodePwd);

		if ( status != 0 ) {
			return LDB_ERR_ENTRY_ALREADY_EXISTS;
		}

	} else if ( is_user || is_group ) {
		ldb_debug(ldb, LDB_DEBUG_ERROR, ("%s: ldb_add of user and group object is disabled\n"), ldb_module_get_name(module));
		return LDB_ERR_UNWILLING_TO_PERFORM;
	}

	return ldb_next_request(module, req);
}

static int univention_samaccountname_ldap_check_init_context(struct ldb_module *module)
{
	struct ldb_context *ldb;

	int ret;
	ret = ldb_mod_register_control(module, LDB_CONTROL_BYPASS_SAMACCOUNTNAME_LDAP_CHECK_OID);
	if (ret != LDB_SUCCESS) {
		ldb = ldb_module_get_ctx(module);
		ldb_debug(ldb, LDB_DEBUG_TRACE,
			"%s: "
			"Unable to register %s control with rootdse.\n"
			"Errormessage: %s\n"
			"This seems to be ok, continuing..",
			LDB_CONTROL_BYPASS_SAMACCOUNTNAME_LDAP_CHECK_NAME,
			ldb_module_get_name(module),
			ldb_errstring(ldb));
	}

	return ldb_next_init(module);
}

static struct ldb_module_ops ldb_univention_samaccountname_ldap_check_module_ops = {
	.name	= "univention_samaccountname_ldap_check",
	.add	= univention_samaccountname_ldap_check_add,
	// .init_context	= univention_samaccountname_ldap_check_init_context,
};

int ldb_univention_samaccountname_ldap_check_init(const char *version)
{
	LDB_MODULE_CHECK_VERSION(version);
	return ldb_register_module(&ldb_univention_samaccountname_ldap_check_module_ops);
}
