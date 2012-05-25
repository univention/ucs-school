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
dojo.require("umc.widgets.StandbyMixin");

// create helper class: combination of Form and StandbyMixin
dojo.declare("umc.modules._internetrules.StandbyForm", [ umc.widgets.Form, umc.widgets.StandbyMixin ], {});

dojo.declare("umc.modules._internetrules.AssignPage", [ umc.widgets.Page, umc.i18n.Mixin ], {
	// summary:
	//		Template module to ease the UMC module development.
	// description:
	//		This module is a template module in order to aid the development of
	//		new modules for Univention Management Console.

	// internal reference to the grid
	_grid: null,

	// use i18n information from umc.modules.internetrules
	i18nClass: 'umc.modules.internetrules',

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
			description: this._('Assign an internet rule to the selected groups'),
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
			label: this._('School'),
			autoHide: true
		}, {
			type: 'TextBox',
			name: 'pattern',
			description: this._('Specifies the substring pattern which is searched for in the group properties'),
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
		if (!ids.length) {
			// ignore an empty set of items
			return;
		}

		// define a cleanup function
		var dialog = null, form = null;
		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		// prepare displayed list of groups
		var message = '';
		var groups = dojo.map(items, function(iitem) {
			return iitem.name;
		});
		if (ids.length > 1) {
			// show groups as a list ul-list
			message = '<ul style="max-height:250px; overflow: auto;"><li>' + groups.join('</li><li>') + '</li></ul>';
			message = '<p>' + this._('The chosen internet rule will be assigned to the following groups:') + '</p>' + message;
		}
		else {
			// only one group
			message = '<p>' + this._('The chosen internet rule will be assigned to the following group: %s', groups[0]) + '</p>';
		}

		// define the formular
		var widgets = [{
			type: 'Text',
			name: 'message',
			content: message
		}, {
			type: 'ComboBox',
			name: 'rule',
			description: this._('Choose the internet rule'),
			label: this._('Internet rule'),
			staticValues: [{
				id: '$default$',
				label: this._('-- default settings --')
			}],
			dynamicValues: function() {
				// query rules mapped to id-label dicts
				return umc.tools.umcpCommand('internetrules/query').then(function(response) {
					return dojo.map(response.result, function(iitem) {
						return iitem.name;
					});
				});
			}
		}];

		// define buttons and callbacks
		var buttons = [{
			name: 'cancel',
			label: this._('Cancel'),
			callback: _cleanup
		}, {
			name: 'submit',
			label: this._('Assign rule'),
			style: 'float:right',
			callback: dojo.hitch(this, function(vals) {
				// prepare parameters
				form.standby(true);
				var rule = form.getWidget('rule').get('value');
				var assignedRules = dojo.map(ids, function(iid) {
					return {
						group: iid,
						rule: rule
					};
				});

				// send UMCP command
				umc.tools.umcpCommand('internetrules/groups/assign', assignedRules).then(dojo.hitch(this, function() {
					// cleanup
					this.moduleStore.onChange();
					_cleanup();
				}), function() {
					// some error occurred
					_cleanup();
				});
			})
		}];

		// generate the search form
		form = new umc.modules._internetrules.StandbyForm({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			widgets: widgets,
			layout: [ 'rule', 'message' ],
			buttons: buttons
		});

		// show the dialog
		dialog = new dijit.Dialog({
			title: this._('Assign internet rule'),
			content: form,
			'class' : 'umcPopup',
			style: 'max-width: 400px;'
		});
		dialog.show();
	}
});



