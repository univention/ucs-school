/*
 * Copyright 2014-2017 Univention GmbH
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
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolwizards/UserWizard",
	"umc/modules/schoolwizards/Grid",
	"umc/modules/schoolwizards/utils",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, SearchBox, ComboBox, UserWizard, Grid, utils, _) {

	return declare("umc.modules.schoolwizards.UserGrid", [Grid], {

		headerText: _('Management of school users'),
		helpText: '',
		objectNamePlural: _('school users'),
		objectNameSingular: _('school user'),
		firstObject: _('the first school user'),
		createObjectWizard: UserWizard,
		sortFields: ['display_name'],

		postCreate: function() {
			this.inherited(arguments);
			this._grid.sortRepresentations.school_classes = lang.hitch(this, 'school_classesFormatter');
		},

		getGridColumnsWithSchool: function() {
			return this.getGridColumns();
		},

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
				name: 'type_name',
				label: _('Role'),
				description: _('Role of the %s.', this.objectNameSingular)
			}, {
				name: 'school_classes',
				label: _('Class'),
				description: _('Class of the %s.', this.objectNameSingular),
				formatter: lang.hitch(this, 'school_classesFormatter')
//			}, {
//				name: 'mailPrimaryAddress',
//				label: _('E-Mail address'),
//				description: _('E-Mail address of the %s.', this.objectNameSingular)
			}];
		},

		school_classesFormatter: function(values) {
			return array.map(values[this.school], lang.hitch(this, function(value) {
				return value.indexOf(this.school + '-') === -1 ? value : value.slice(this.school.length + 1);
			})).join(', ');
		},

		getObjectIdName: function(item) {
			return item.name;
		},

		getSearchLayout: function() {
			return [['school', 'type', 'filter']];
		},

		getDeleteConfirmMessage: function(objects) {
			var msg = _('Please confirm to delete the %(num)d selected %(objectNamePlural)s from school %(school)s.', {num: objects.length, objectNamePlural: this.objectNamePlural, school: this.schoolLabel});
			if (objects.length === 1) {
				msg = _('Please confirm to delete %(objectNameSingular)s "%(objectName)s" from school %(school)s.', {objectNameSingular: this.objectNameSingular, objectName: this.getObjectIdName(objects[0]), school: this.schoolLabel});
			}
			return msg;
		},

		getSearchWidgets: function() {
			var schools = lang.clone(this.schools);
			if (schools.length > 1) {
				schools.unshift({id: '/', label: _('All')});
			}
			return [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				size: 'TwoThirds',
				staticValues: schools,
				autoHide: true
			}, {
				type: ComboBox,
				name: 'type',
				label: _('Role'),
				size: 'TwoThirds',
				sortDynamicValues: false,
				dynamicValues: utils.getStaticValuesUserRolesWithAll
			}, {
				type: SearchBox,
				size: 'TwoThirds',
				name: 'filter',
				label: _('Filter'),
				inlineLabel: _('Search...'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];
		}
	});
});
