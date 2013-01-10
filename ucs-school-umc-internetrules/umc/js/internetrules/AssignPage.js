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
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dijit/Dialog",
	"umc/tools",
	"umc/store",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Grid",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/SearchForm",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/internetrules"
], function(declare, lang, array, Dialog, tools, store, Page, Form, ExpandingTitlePane,
            Grid, TextBox, Text, ComboBox, SearchForm, StandbyMixin, _) {

// create helper class: combination of Form and StandbyMixin
var StandbyForm = declare("umc.modules.internetrules.StandbyForm", [ Form, StandbyMixin ], {});

	return declare("umc.modules.internetrules.AssignPage", [ Page ], {
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
			this.headerText = _('Assignment of internet rules');
			this.moduleStore = store('$dn$', 'internetrules/groups');
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
				name: 'assign',
				label: _('Assign rule'),
				description: _('Assign an internet rule to the selected groups'),
				isStandardAction: true,
				isMultiAction: true,
				callback: lang.hitch(this, '_assignRule')
			}];

			// define the grid columns
			var columns = [{
				name: 'name',
				label: _('Group name'),
				width: '50%'
			}, {
				name: 'rule',
				label: _('Associated rule'),
				width: '50%'
			}];

			// generate the data grid
			this._grid = new Grid({
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
				type: ComboBox,
				name: 'school',
				dynamicValues: 'internetrules/schools',
				label: _('School'),
				autoHide: true
			}, {
				type: TextBox,
				name: 'pattern',
				description: _('Specifies the substring pattern which is searched for in the group properties'),
				label: _('Search pattern')
			}];

			this._searchForm = new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: [ [ 'school', 'pattern', 'submit' ] ],
				onSearch: lang.hitch(this, function(values) {
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
			var _dialog = null, form = null;
			var _cleanup = function() {
				_dialog.hide();
				_dialog.destroyRecursive();
				form.destroyRecursive();
			};

			// prepare displayed list of groups
			var message = '';
			var groups = array.map(items, function(iitem) {
				return iitem.name;
			});
			if (ids.length > 1) {
				// show groups as a list ul-list
				message = '<ul style="max-height:250px; overflow: auto;"><li>' + groups.join('</li><li>') + '</li></ul>';
				message = '<p>' + _('The chosen internet rule will be assigned to the following groups:') + '</p>' + message;
			}
			else {
				// only one group
				message = '<p>' + _('The chosen internet rule will be assigned to the following group: %s', groups[0]) + '</p>';
			}

			// define the formular
			var widgets = [{
				type: Text,
				name: 'message',
				content: message
			}, {
				type: ComboBox,
				name: 'rule',
				description: _('Choose the internet rule'),
				label: _('Internet rule'),
				staticValues: [{
					id: '$default$',
					label: _('-- default settings --')
				}],
				dynamicValues: function() {
					// query rules mapped to id-label dicts
					return tools.umcpCommand('internetrules/query').then(function(response) {
						return array.map(response.result, function(iitem) {
							return iitem.name;
						});
					});
				}
			}];

			// define buttons and callbacks
			var buttons = [{
				name: 'cancel',
				label: _('Cancel'),
				callback: _cleanup
			}, {
				name: 'submit',
				label: _('Assign rule'),
				style: 'float:right',
				callback: lang.hitch(this, function(vals) {
					// prepare parameters
					form.standby(true);
					var rule = form.getWidget('rule').get('value');
					var assignedRules = array.map(ids, function(iid) {
						return {
							group: iid,
							rule: rule
						};
					});

					// send UMCP command
					tools.umcpCommand('internetrules/groups/assign', assignedRules).then(lang.hitch(this, function() {
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
			form = new StandbyForm({
				// property that defines the widget's position in a dijit.layout.BorderContainer
				widgets: widgets,
				layout: [ 'rule', 'message' ],
				buttons: buttons
			});

			// show the dialog
			_dialog = new Dialog({
				title: _('Assign internet rule'),
				content: form,
				'class' : 'umcPopup',
				style: 'max-width: 400px;'
			});
			_dialog.show();
		}
	});

});
