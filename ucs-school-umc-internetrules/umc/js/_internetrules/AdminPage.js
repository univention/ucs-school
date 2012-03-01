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
		this.moduleStore = umc.store.getModuleStore('id', 'internetrules');
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
			callback: dojo.hitch(this, '_dummy')
		}, {
			name: 'edit',
			label: this._('Edit'),
			description: this._('Edit the selected rule'),
			iconClass: 'umcIconEdit',
			isStandardAction: true,
			isMultiAction: false,
			callback: dojo.hitch(this, '_editRule')
		}, {
			name: 'delete',
			label: this._('Delete'),
			description: this._('Delete the selected rules.'),
			isStandardAction: true,
			isMultiAction: true,
			iconClass: 'umcIconDelete',
			callback: dojo.hitch(this, '_dummy')
		}];

		// define the grid columns
		var columns = [{
			name: 'name',
			label: this._('Name'),
			width: '25%'
		}, {
			name: 'type',
			label: this._('Type'),
			width: '25%'
		}, {
			name: 'groups',
			label: this._('Associated groups'),
			width: '50%'
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

	_dummy: function() {
		umc.dialog.alert(this._('Feature not yet implemented'));
	},

	_editRule: function(ids, items) {
		if (ids.length != 1) {
			// should not happen
			return;
		}

		// send event in order to load the particular rule
		this.onOpenDetailPage(ids[0]);
	},

	onOpenDetailPage: function(id) {
		// event stub
	}
});



