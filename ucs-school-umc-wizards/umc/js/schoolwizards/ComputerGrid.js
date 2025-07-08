/*
 * SPDX-FileCopyrightText: 2014-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */

/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolwizards/ComputerWizard",
	"umc/modules/schoolwizards/Grid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, SearchBox, ComboBox, ComputerWizard, Grid, _) {

	return declare("umc.modules.schoolwizards.ComputerGrid", [Grid], {

		headerText: _('Management of school computers'),
		helpText: '',
		objectNamePlural: _('computers'),
		objectNameSingular: _('computer'),
		firstObject: _('the first computer'),
		createObjectWizard: ComputerWizard,

		getGridColumns: function() {
			return [{
				name: 'name',
				label: _('Name')
			}, {
				name: 'type_name',
				label: _('Computer type')
			}, {
				name: 'ip_address',
				label: _('IP address')
			}, {
				name: 'mac_address',
				label: _('MAC address')
			}, {
				name: 'inventory_number',
				label: _('Inventory number')
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
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
				size: 'TwoThirds',
				name: 'type',
				label: _('Computer type'),
				dynamicValues: 'schoolwizards/computers/types',
				umcpCommand: lang.hitch(this, function() {
					return this.umcpCommand.apply(this.umcpCommand, arguments).then(function(response) {
						response.result.unshift({
							id: 'all',
							label: _('All')
						});
						return response;
					});
				}),
				sortDynamicValues: false
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
			return [['school', 'type', 'filter']];
		}
	});
});
