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

dojo.provide("umc.modules._internetrules.AssignPage");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.store");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.Grid");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.SearchForm");

dojo.declare("umc.modules._internetrules.AssignPage", [ umc.widgets.Page, umc.i18n.Mixin ], {
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
		this.headerText = this._('Assignment of internet rules');
		this.moduleStore = umc.store.getModuleStore('$dn$', 'internetrules/groups');
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
			name: 'assign',
			label: this._('Assign rule'),
			description: this._('Assigne internet rules to selected groups'),
			isStandardAction: true,
			isMultiAction: true,
			callback: dojo.hitch(this, '_assignRule')
		}];

		// define the grid columns
		var columns = [{
			name: 'name',
			label: this._('Group name'),
			width: '50%'
		}, {
			name: 'rule',
			label: this._('Associated rule'),
			width: '50%'
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			actions: actions,
			columns: columns,
			moduleStore: this.moduleStore,
			// initial query
			query: { colors: 'None', name: '' },
			defaultAction: 'assign'
		});

		// add the grid to the title pane
		titlePane.addChild(this._grid);

		//
		// search form
		//

		var widgets = [{
			type: 'ComboBox',
			name: 'school',
			dynamicValues: 'internetrules/schools',
			label: this._('School')
			//autoHide: true
		}, {
			type: 'TextBox',
			name: 'pattern',
			description: this._('Specifies the substring pattern which is searched for in the rules\' name and groups'),
			label: this._('Search pattern')
		}];

		this._searchForm = new umc.widgets.SearchForm({
			region: 'top',
			widgets: widgets,
			layout: [ [ 'school', 'pattern', 'submit' ] ],
			onSearch: dojo.hitch(this, function(values) {
				this._grid.filter(values);
			})
		});

		// add search form to the title pane
		titlePane.addChild(this._searchForm);
	},

	_assignRule: function(ids, items) {
		// define a cleanup function
		var dialog = null, form = null;
		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		// add remaining elements of the search form
		var groups = dojo.map(items, function(iitem) {
			return iitem.name;
		}).join(', ');
		var message = this._('Please choose an internet rule that is assigned to the following groups: %s', [ groups ]);
		var widgets = [{
			type: 'Text',
			name: 'message',
			content: '<p>' + message + '</p>'
		}, {
			type: 'ComboBox',
			name: 'rule',
			description: this._('Choose the internet rule'),
			label: this._('Internet rule'),
			dynamicValues: function() {
				// query rules mapped to id-label dicts
				return umc.tools.umcpCommand('internetrules/query').then(function(response) {
					return dojo.map(response.result, function(iitem) {
						return { id: iitem.id, label: iitem.name };
					});
				});
			}
		}];

		// define buttons and callbacks
		var buttons = [{
			name: 'submit',
			label: this._('Assign rule'),
			style: 'float:right',
			callback: dojo.hitch(this, function(vals) {
				// reload the grid
				this._grid.filter({ pattern: this._searchForm.getWidget('pattern').get('value') });

				// destroy the dialog
				_cleanup();
			})
		}, {
			name: 'cancel',
			label: this._('Cancel'),
			callback: _cleanup
		}];

		// generate the search form
		form = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			widgets: widgets,
			layout: [ 'message', 'rule' ],
			buttons: buttons
		});

		// show the dialog
		dialog = new dijit.Dialog({
			title: this._('Assign internet rules'),
			content: form,
			'class' : 'umcPopup',
			style: 'max-width: 400px;'
		});
		dialog.show();
	}
});



