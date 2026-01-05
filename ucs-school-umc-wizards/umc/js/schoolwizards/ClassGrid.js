/*
 * SPDX-FileCopyrightText: 2014-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */

/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolwizards/ClassWizard",
	"umc/modules/schoolwizards/Grid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, SearchBox, ComboBox, ClassWizard, Grid, _) {

	return declare("umc.modules.schoolwizards.ClassGrid", [Grid], {

		headerText: _('Management of school classes'),
		helpText: '',
		objectNamePlural: _('classes'),
		objectNameSingular: _('class'),
		firstObject: _('the first class'),
		createObjectWizard: ClassWizard,

		getGridColumns: function() {
			return [{
				name: 'name',
				label: _('Name')
			}, {
				name: 'description',
				label: _('Description')
			}];
		},

		getObjectIdName: function(item) {
			return item.name;
		},

		getSearchWidgets: function() {
			var schools = lang.clone(this.schools);
			if (schools.length > 1) {
				schools.unshift({id: '/', label: _('All')});
			}
			return [{
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
				size: 'TwoThirds',
				name: 'school',
				label: _('School'),
				staticValues: schools,
				autoHide: true
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
		},

		getSearchLayout: function() {
			return [['school', 'filter']];
		}
	});
});
