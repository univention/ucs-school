/*
 * Copyright 2014 Univention GmbH
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

/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/topic",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolwizards/UserWizard",
	"umc/modules/schoolwizards/Grid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, topic, TextBox, ComboBox, UserWizard, Grid, _) {

	return declare("umc.modules.schoolwizards.UserGrid", [Grid], {

		headerText: _('Management of school users'),
		helpText: '',
		objectNamePlural: _('users'),
		objectNameSingular: _('user'),
		createObjectWizard: UserWizard,

		getGridColumns: function() {
			return [{
				name: 'display_name',
				label: _('Name'),
				formatter: lang.hitch(this, function(nothing, id) {
					var item = this._grid.getRowValues(id);
					return '' + item.display_name + ' (' + item.name + ')';
				}),
				description: _('Name of the %s.', this.objectNameSingular)
			}, {
				name: 'role_name',
				label: _('Role'),
				description: _('Role of the %s.', this.objectNameSingular)
			}, {
				name: 'school_class',
				label: _('Class'),
				description: _('Class of the %s.', this.objectNameSingular)
//			}, {
//				name: 'mailPrimaryAddress',
//				label: _('E-Mail address'),
//				description: _('E-Mail address of the %s.', this.objectNameSingular)
			}, {
				name: 'empty',  // workaround: EnhancedGrid
				label: '&nbsp;',
				width: '10px',
				formatter: function() { return ''; }
			}];
		},

		getObjectIdName: function(item) {
			return item.name;
		},

		getSearchLayout: function() {
			return [['school', 'type', 'filter', 'submit']];
		},

		getSearchWidgets: function() {
			return [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				size: 'TwoThirds',
				staticValues: this.schools,
				autoHide: true
			}, {
				type: ComboBox,
				name: 'type',
				label: _('Role'),
				size: 'TwoThirds',
				staticValues: [{
					id: 'all',
					label: _('All')
				}, {
					id: 'student',
					label: _('Student')
				}, {
					id: 'teacher',
					label: _('Teacher')
				}, {
					id: 'staff',
					label: _('Staff')
				}, {
					id: 'teachersAndStaff',
					label: _('Teachers and staff')
				}]
			}, {
				type: TextBox,
				size: 'TwoThirds',
				name: 'filter',
				label: _('Filter')
			}];
		}
	});
});
