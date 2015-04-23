/*
 * Copyright 2015 Univention GmbH
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
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolgroups/DetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, MultiObjectSelect, TextBox, ComboBox, DetailPage, _) {

	return declare("umc.modules.schoolgroups.WorkgroupDetailPage", [DetailPage], {
		getWidgets: function() {
			return [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				staticValues: []
			}, {
				type: TextBox,
				name: 'name',
				label: _('Workgroup'),
				disabled: this.moduleFlavor != 'workgroup-admin',
				regExp: '^[a-zA-Z0-9]([a-zA-Z0-9 _.-]*[a-zA-Z0-9])?$',
				invalidMessage: _('May only consist of letters, digits, spaces, dots, hyphens, underscore. Has to start and to end with a letter or a digit.'),
				required: true
			}, {
				type: TextBox,
				name: 'description',
				label: _('Description'),
				description: _('Verbose description of the group'),
				disabled: this.moduleFlavor != 'workgroup-admin'
			}, this.getMultiSelectWidget()];
		},

		getMultiSelectWidget: function() {
			return lang.mixin(this.inherited(arguments), {
				label: this.moduleFlavor == 'workgroup' ? _('Students') : _('Members'),
				description: _('Teachers and students that belong to the current workgroup'),
				queryOptions: lang.hitch(this, function() {
					if (this.moduleFlavor == 'workgroup') {
						return { group: 'student' };
					}
					return {};
				})
			});
		},
		getMultiSelectGroup: function() {
			var groups = [];
			if (this.moduleFlavor == 'workgroup-admin') {
				groups.push({id: 'None', label: _('All users')});
				groups.push({id: 'teacher', label: _('All teachers')});
			}
			groups.push({id: 'student', label: _('All students')});
			return lang.mixin(this.inherited(arguments), {
				staticValues: groups
			});
		}

	});
});
