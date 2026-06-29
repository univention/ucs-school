/*
 * SPDX-FileCopyrightText: 2014-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */

/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojox/html/entities",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/widgets/Text",
	"umc/widgets/Tooltip",
	"umc/modules/schoolwizards/UserWizard",
	"umc/modules/schoolwizards/Grid",
	"umc/modules/schoolwizards/utils",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, entities, SearchBox, ComboBox, Text, Tooltip, UserWizard, Grid, utils, _) { // eslint-disable-line max-params

	return declare("umc.modules.schoolwizards.UserGrid", [Grid], {

		headerText: _('Management of school users'),
		helpText: '',
		objectNamePlural: _('school users'),
		objectNameSingular: _('school user'),
		firstObject: _('the first school user'),
		createObjectWizard: UserWizard,
		sortFields: ['display_name'],

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
				formatter: lang.hitch(this, 'school_classesCell'),
				sortFormatter: lang.hitch(this, 'school_classesFormatter')
			}, {
				name: 'disabled',
				label: _('Account status'),
				formatter: function(value) {
					if (value === '1') {
						return _('Deactivated');
					} else {
						return _('Activated');
					}
				}
			}];
		},

		_sortedSchoolClasses: function(values) {
			// language-aware sort; numeric so '2a' sorts before '10a'
			const classes = (values[this.school] || []).slice().sort(function(a, b) {
				return a.localeCompare(b, undefined, {numeric: true});
			});
			// drop the redundant '<school>-' prefix; the grid is scoped to one school
			return array.map(classes, lang.hitch(this, function(value) {
				return value.indexOf(this.school + '-') === -1 ? value : value.slice(this.school.length + 1);
			}));
		},

		school_classesFormatter: function(values) {
			return this._sortedSchoolClasses(values).join(', ');
		},

		school_classesCell: function(values) {
			const content = this._sortedSchoolClasses(values).join(', ');
			const widget = new Text({
				content: entities.encode(content)
			});
			this.own(widget);
			// the cell truncates with an ellipsis; the tooltip shows the full list
			if (content) {
				const tooltip = new Tooltip({
					label: entities.encode(content),
					connectId: [widget.domNode],
					position: ['below', 'above']
				});
				widget.own(tooltip);
			}
			return widget;
		},

		getObjectIdName: function(item) {
			return item.name;
		},

		getSearchLayout: function() {
			return [['school', 'type', 'accountStatus', 'filter']];
		},

		getDeleteConfirmMessage: function(objects) {
			var msg = _('Please confirm to delete the %(num)d selected %(objectNamePlural)s from school %(school)s.', {num: objects.length, objectNamePlural: this.objectNamePlural, school: entities.encode(this.schoolLabel)});
			if (objects.length === 1) {
				msg = _('Please confirm to delete %(objectNameSingular)s "%(objectName)s" from school %(school)s.', {objectNameSingular: this.objectNameSingular, objectName: this.getObjectIdName(objects[0]), school: entities.encode(this.schoolLabel)});
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
				'class': 'umcTextBoxOnBody',
				name: 'school',
				label: _('School'),
				size: 'TwoThirds',
				staticValues: schools,
				autoHide: true
			}, {
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
				name: 'type',
				label: _('Role'),
				size: 'TwoThirds',
				sortDynamicValues: false,
				dynamicValues: utils.getStaticValuesUserRolesWithAll
			}, {
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
				name: 'accountStatus',
				label: _('Account status'),
				size: 'TwoThirds',
				staticValues: [{
					id: 'all',
					label: _('All'),
				}, {
					id: 'activated',
					label: _('Activated'),
				}, {
					id: 'deactivated',
					label: _('Deactivated'),
				}],
			}, {
				type: SearchBox,
				'class': 'umcTextBoxOnBody',
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
