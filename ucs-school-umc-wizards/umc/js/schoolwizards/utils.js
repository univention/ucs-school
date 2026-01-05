/*
 * SPDX-FileCopyrightText: 2017-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */

define([
	"dojo/_base/array",
	"umc/tools",
	"umc/i18n!umc/modules/schoolwizards"
], function(array, tools, _) {
	var utils = {
		_ucr: null,

		getUcr: function() {
			if (!utils._ucr) {
				utils._ucr = tools.ucr([
					'ucsschool/wizards/schoolwizards/users/roles/disabled'
				]);
			}
			return utils._ucr;
		},

		getStaticValuesUserRoles: function(withAll) {
			// return a deferred object that returns a list of UCS@school user roles that
			// also includes the role 'all' if the argument withAll is true.
			return utils.getUcr().then(function(ucrVariables) {
				var disabledRoles = ucrVariables['ucsschool/wizards/schoolwizards/users/roles/disabled'];

				disabledRoles = (disabledRoles === null) ? [] : disabledRoles.split(/[ ,]+/);

				var idAndLabel = [
					['all', _('All')],
					['student', _('Student')],
					['teacher', _('Teacher')],
					['legalGuardian', _('Legal guardian')],
					['staff', _('Staff')],
					['teachersAndStaff', _('Teachers and staff')],
					['schoolAdmin', _('School Administrator')]
				];

				var roleValues = [];
				array.forEach(idAndLabel, function(entry) {
					if ((disabledRoles.indexOf(entry[0]) < 0) && ((withAll) || (entry[0] != 'all'))) {
						roleValues.push({
							id: entry[0],
							label: entry[1]
						});
					}
				});
				return roleValues;
			});
		},

		getStaticValuesUserRolesWithAll: function() {
			// see getStaticValuesUserRoles
			// returned list contains 'all' entry
			return utils.getStaticValuesUserRoles(true);
		},

		getStaticValuesUserRolesWithoutAll: function() {
			// see getStaticValuesUserRoles
			// returned list does not contain 'all' entry
			return utils.getStaticValuesUserRoles(false);
		}
	};
	return utils;
});
