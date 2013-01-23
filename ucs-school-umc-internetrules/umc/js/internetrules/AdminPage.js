/*
 * Copyright 2012-2013 Univention GmbH
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
	"umc/dialog",
	"umc/store",
	"umc/widgets/Page",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Grid",
	"umc/widgets/TextBox",
	"umc/widgets/SearchForm",
	"umc/i18n!umc/modules/internetrules"
], function(declare, lang, array, dialog, store, Page, ExpandingTitlePane, Grid, TextBox, SearchForm, _) {

	return declare("umc.modules.internetrules.AdminPage", [ Page ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

		// internal reference to the grid
		_grid: null,

		// reference to the module store used
		moduleStore: null,

		postMixInProperties: function() {
			this.inherited(arguments);
			this.headerText = _('Administration of internet rules');
			this.moduleStore = store('name', 'internetrules');
		},

		buildRendering: function() {
			this.inherited(arguments);

			// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
			var titlePane = new ExpandingTitlePane({
				title: _('Search results')
			});
			this.addChild(titlePane);

			//
			// data grid
			//

			// define grid actions
			var actions = [{
				name: 'add',
				label: _('Add rule'),
				description: _('Create a new rule'),
				iconClass: 'umcIconAdd',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_add')
			}, {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected rule'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_edit')
			}, {
				name: 'delete',
				label: _('Delete'),
				description: _('Delete the selected rules.'),
				isStandardAction: true,
				isMultiAction: true,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_remove')
			}];

			// define the grid columns
			var columns = [{
				name: 'name',
				label: _('Name'),
				width: 'auto'
			}, {
				name: 'type',
				label: _('Type'),
				width: '100px',
				formatter: lang.hitch(this, function(type) {
					if (type == 'whitelist') {
						return _('whitelist');
					}
					else if (type == 'blacklist') {
						return _('blacklist');
					}
					return _('Unknown');
				})
			}, {
				name: 'wlan',
				label: _('Wifi'),
				width: '100px',
				formatter: lang.hitch(this, function(wlan) {
					return wlan ? _('enabled') : _('disabled');
				})
			}, {
				name: 'priority',
				label: _('Priority'),
				width: 'adjust'
			}];

			// generate the data grid
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore
			});

			// add the grid to the title pane
			titlePane.addChild(this._grid);

			//
			// search form
			//

			var widgets = [{
				type: TextBox,
				name: 'pattern',
				description: _('Specifies the substring pattern which is searched for in the rules\' name and its domain list'),
				label: _('Search pattern')
			}];

			this._searchForm = new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: [ [ 'pattern', 'submit' ] ],
				onSearch: lang.hitch(this, function(values) {
					this._grid.filter(values);
				})
			});
			// initial query
			this._searchForm.on('valuesInitialized', lang.hitch(this, function() { this._searchForm.submit(); }));

			// add search form to the title pane
			titlePane.addChild(this._searchForm);
		},

		_edit: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			// send event in order to load the particular rule
			this.onOpenDetailPage(ids[0]);
		},

		_add: function() {
			// send event in order to load an empty page
			this.onOpenDetailPage();
		},

		_remove: function(ids, items) {
			if (ids.length < 1) {
				// should not happen
				return;
			}

			// get a string of all rule names and the correct confirmation message
			var rulesStr = array.map(items, function(iitem) {
				return iitem.name;
			}).join('</li><li>');
			rulesStr = '<ul style="max-height:200px; overflow:auto;"><li>' + rulesStr + '</li></ul>';
			var confirmMsg = items.length > 1 ? _('Please confirm to remove the following %d filter rules: %s', items.length, rulesStr) : _('Please confirm to remove the following filter rule: %s', rulesStr);

			// ask for confirmation
			dialog.confirm(confirmMsg, [{
				label: _('Cancel'),
				name: 'cancel',
				'default': true
			}, {
				label: items.length > 1 ? _('Remove rules') : _('Remove rule'),
				name: 'remove'
			}]).then(lang.hitch(this, function(response) {
				if (response === 'remove') {
					// ok, remove all rules, one by one using a transaction
					var transaction = this.moduleStore.transaction();
					array.forEach(ids, function(iid) {
						this.moduleStore.remove(iid);
					}, this);
					transaction.commit().then(lang.hitch(this, function(result) {
						var failedRules = array.filter(result, function(iresult) {
							return !iresult.success;
						});
						if (failedRules.length) {
							// something went wrong... display the rules for which the removal failed
							var rulesStr = array.map(failedRules, function(iresult) {
								return iresult.name;
							}).join('</li><li>');
							rulesStr = '<ul style="max-height:200px; overflow:auto;"><li>' + rulesStr + '</li></ul>';
							dialog.alert(_('Removal of the following rules failed:%s', rulesStr));
						}
					}));
				}
			}));
		},

		onOpenDetailPage: function(id) {
			// event stub
		}
	});

});
