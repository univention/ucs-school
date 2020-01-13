/*
 * Copyright 2017-2020 Univention GmbH
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
					['staff', _('Staff')],
					['teachersAndStaff', _('Teachers and staff')]
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
