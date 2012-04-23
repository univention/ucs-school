/*
 * Copyright 2012 Univention GmbH
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
/*global console dojo dojox dijit umc */

dojo.provide("umc.modules._internetrules.AdminPage");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.store");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.Grid");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.SearchForm");

dojo.declare("umc.modules._internetrules.AdminPage", [ umc.widgets.Page, umc.i18n.Mixin ], {
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
		this.headerText = this._('Administration of internet rules');
		this.moduleStore = umc.store.getModuleStore('name', 'internetrules');
	},

	buildRendering: function() {
		this.inherited(arguments);

		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		var titlePane = new umc.widgets.ExpandingTitlePane({
			title: this._('Search results')
		});
		this.addChild(titlePane);

		//
		// data grid
		//

		// define grid actions
		var actions = [{
			name: 'add',
			label: this._('Add rule'),
			description: this._('Create a new rule'),
			iconClass: 'umcIconAdd',
			isContextAction: false,
			isStandardAction: true,
			callback: dojo.hitch(this, '_add')
		}, {
			name: 'edit',
			label: this._('Edit'),
			description: this._('Edit the selected rule'),
			iconClass: 'umcIconEdit',
			isStandardAction: true,
			isMultiAction: false,
			callback: dojo.hitch(this, '_edit')
		}, {
			name: 'delete',
			label: this._('Delete'),
			description: this._('Delete the selected rules.'),
			isStandardAction: true,
			isMultiAction: true,
			iconClass: 'umcIconDelete',
			callback: dojo.hitch(this, '_remove')
		}];

		// define the grid columns
		var columns = [{
			name: 'name',
			label: this._('Name'),
			width: 'auto'
		}, {
			name: 'type',
			label: this._('Type'),
			width: '100px',
			formatter: dojo.hitch(this, function(type) {
				if (type == 'whitelist') {
					return this._('whitelist');
				}
				else if (type == 'blacklist') {
					return this._('blacklist');
				}
				return this._('Unknown');
			})
		}, {
			name: 'wlan',
			label: this._('Wifi'),
			width: '100px',
			formatter: dojo.hitch(this, function(wlan) {
				return wlan ? this._('enabled') : this._('disabled');
			})
		}, {
			name: 'priority',
			label: this._('Priority'),
			width: 'adjust'
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			actions: actions,
			columns: columns,
			moduleStore: this.moduleStore,
			// initial query
			query: { colors: 'None', name: '' }
		});

		// add the grid to the title pane
		titlePane.addChild(this._grid);

		//
		// search form
		//

		var widgets = [{
			type: 'TextBox',
			name: 'pattern',
			description: this._('Specifies the substring pattern which is searched for in the rules\' name and groups'),
			label: this._('Search pattern')
		}];

		this._searchForm = new umc.widgets.SearchForm({
			region: 'top',
			widgets: widgets,
			layout: [ [ 'pattern', 'submit' ] ],
			onSearch: dojo.hitch(this, function(values) {
				this._grid.filter(values);
			})
		});

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
		var rulesStr = dojo.map(items, function(iitem) {
			return iitem.name;
		}).join('</li><li>');
		rulesStr = '<ul style="max-height:200px; overflow:auto;"><li>' + rulesStr + '</li></ul>';
		var confirmMsg = items.length > 1 ? this._('Please confirm to remove the following %d filter rules: %s', items.length, rulesStr) : this._('Please confirm to remove the following filter rule: %s', rulesStr);

		// ask for confirmation
		umc.dialog.confirm(confirmMsg, [{
			label: this._('Cancel'),
			name: 'cancel',
			'default': true
		}, {
			label: items.length > 1 ? this._('Remove rules') : this._('Remove rule'),
			name: 'remove'
		}]).then(dojo.hitch(this, function(response) {
			if (response === 'remove') {
				// ok, remove all rules, one by one using a transaction
				var transaction = this.moduleStore.transaction();
				dojo.forEach(ids, function(iid) {
					this.moduleStore.remove(iid);
				}, this);
				transaction.commit().then(dojo.hitch(this, function(result) {
					var failedRules = dojo.filter(result, function(iresult) {
						return !iresult.success;
					});
					if (failedRules.length) {
						// something went wrong... display the rules for which the removal failed
						var rulesStr = dojo.map(failedRules, function(iresult) {
							return iresult.name;
						}).join('</li><li>');
						rulesStr = '<ul style="max-height:200px; overflow:auto;"><li>' + rulesStr + '</li></ul>';
						umc.dialog.alert(this._('Removal of the following rules failed:%s', rulesStr));
					}
				}));
			}
		}));
	},

	onOpenDetailPage: function(id) {
		// event stub
	}
});



