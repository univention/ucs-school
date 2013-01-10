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
	"umc/dialog",
	"umc/tools",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/distribution/DetailPage",
	"umc/i18n!umc/modules/distribution"
], function(declare, lang, dialog, tools, ExpandingTitlePane, Grid, Module, Page, SearchForm, TextBox, ComboBox, DetailPage, _) {

	return declare("umc.modules.distribution", [ Module ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

		// the property field that acts as unique identifier for the object
		idProperty: 'name',

		// internal reference to the grid
		_grid: null,

		// internal reference to the search page
		_searchPage: null,

		// internal reference to the detail page for editing an object
		_detailPage: null,

		postMixInProperties: function() {
			// is called after all inherited properties/methods have been mixed
			// into the object (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			// Set the opacity for the standby animation to 100% in order to mask
			// GUI changes when the module is opened. Call this.standby(true|false)
			// to enabled/disable the animation.
			this.standbyOpacity = 1;
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			// render the page containing search form and grid
			this.renderSearchPage();
		},

		renderSearchPage: function(containers, superordinates) {
			// render all GUI elements for the search formular and the grid

			// setup search page and its main widgets
			// for the styling, we need a title pane surrounding search form and grid
			this._searchPage = new Page({
				headerText: this.description,
				helpText: ''
			});

			// umc.widgets.Module is also a StackContainer instance that can hold
			// different pages (see also umc.widgets.TabbedModule)
			this.addChild(this._searchPage);

			// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
			var titlePane = new ExpandingTitlePane({
				title: _('Search results')
			});
			this._searchPage.addChild(titlePane);


			//
			// data grid
			//

			// define grid actions
			var actions = [{
				name: 'add',
				label: _('Add project'),
				description: _('Create a new distribution project'),
				iconClass: 'umcIconAdd',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_newObject')
			}, {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected distribution project'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}, {
				name: 'distribute',
				label: lang.hitch(this, function(item) {
					if (!item) {
						return _('Distribution');
					}
					return !item.isDistributed ? _('distribute') : _('collect');
				}),
				description: _('Distribute/collect project files to/from users'),
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_distribute')
			}, {
				name: 'adopt',
				label: lang.hitch(this, function(item) {
					if (!item) {
						return _('Adoption');
					}
					return _('adopt');
				}),
				canExecute: function(item) {
					return item.sender != tools.status('username');
				},
				description: _('Transfer the ownership of the selected project to your account.'),
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_adopt')
			}, {
				name: 'remove',
				label: _('Remove'),
				description: _('Removes the project from the internal database'),
				isStandardAction: true,
				isMultiAction: false,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_delete')
			}];

			// define the grid columns
			var columns = [{
				name: 'description',
				label: _('Description'),
				width: 'auto'
			}, {
				name: 'sender',
				label: _('Owner'),
				width: '175px'
			}, {
				name: 'isDistributed',
				label: _('Status'),
				width: '80px',
				formatter: lang.hitch(this, function(isDistributed) {
					return isDistributed ? _('distributed') : '';
				})
			}, {
				name: 'files',
				label: _('#Files'),
				width: 'adjust'
			}];

			// generate the data grid
			this._grid = new Grid({
				// property that defines the widget's position in a dijit.layout.BorderContainer,
				// 'center' is its default value, so no need to specify it here explicitely
				// region: 'center',
				actions: actions,
				// defines which data fields are displayed in the grids columns
				columns: columns,
				// a generic UMCP module store object is automatically provided
				// as this.moduleStore (see also store.getModuleStore())
				moduleStore: this.moduleStore,
				// initial query
				query: { pattern: '' }
			});

			// add the grid to the title pane
			titlePane.addChild(this._grid);


			//
			// search form
			//

			// add remaining elements of the search form
			var widgets = [{
				type: ComboBox,
				name: 'filter',
				label: 'Filter',
				staticValues: [
					{ id: 'private', label: _('Only own projects') },
					{ id: 'all', label: _('All projects') }
				]
			}, {
				type: TextBox,
				name: 'pattern',
				description: _('Specifies the substring pattern which is searched for in the projects'),
				label: _('Search pattern')
			}];

			// the layout is an 2D array that defines the organization of the form elements...
			// here we arrange the form elements in one row and add the 'submit' button
			var layout = [
				[ 'filter', 'pattern', 'submit' ]
			];

			// generate the search form
			this._searchForm = new SearchForm({
				// property that defines the widget's position in a dijit.layout.BorderContainer
				region: 'top',
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					// call the grid's filter function
					this._grid.filter(values);
				})
			});

			// add search form to the title pane
			titlePane.addChild(this._searchForm);

			//
			// conclusion
			//

			// we need to call page's startup method manually as all widgets have
			// been added to the page container object
			this._searchPage.startup();

			// create a DetailPage instance
			this._detailPage = new DetailPage({
				moduleStore: this.moduleStore,
				moduleFlavor: this.moduleFlavor,
				umcpCommand: lang.hitch(this, 'umcpCommand')
			});
			this.addChild(this._detailPage);

			// connect to the onClose event of the detail page... we need to manage
			// visibility of sub pages here
			// ...will destroy signal handlers upon widget
			// destruction automatically
			this._detailPage.on('close', lang.hitch(this, function() {
				this.selectChild(this._searchPage);
			}));
		},

		_distribute: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			if (!items[0].recipients) {
				// no recipients have been added to project, abort
				dialog.alert(_('Error: No recipients have been assign to the project!'));
				return;
			}

			if (!items[0].files) {
				// no files have been added to project, abort
				dialog.alert(_('Error: No files have been assign to the project!'));
				return;
			}

			var msg = items[0].isDistributed ?
				_('Please confirm to collect the project: %s', items[0].name) :
				_('Please confirm to distribute the project: %s', items[0].name);
			dialog.confirm(msg, [{
				label: _('Cancel'),
				name: 'cancel'
			}, {
				label: items[0].isDistributed ? _('Collect project') : _('Distribute project'),
				name: 'doit',
				'default': true
			}]).then(lang.hitch(this, function(response) {
				if (response === 'doit') {
					this.standby(true);

					// collect or distribute the project, according to its current state
					var cmd = items[0].isDistributed ? 'distribution/collect' : 'distribution/distribute';
					this.umcpCommand(cmd, ids).then(lang.hitch(this, function(response) {
						this.standby(false);

						// prompt any errors to the user
						if (response.result instanceof Array && response.result.length > 0) {
							var res = response.result[0];
							if (!res.success) {
								dialog.alert(_('The following error occurred: %s', res.details));
							}
							else {
								if (items[0].isDistributed) {
									dialog.notify(_('The project files have been collected successfully.'));
								}
								else {
									dialog.notify(_('The project files have been distributed successfully.'));
								}
							}
						}

						// update the grid if a project has been distributed
						if (!items[0].isDistributed) {
							this.moduleStore.onChange();
						}
					}), lang.hitch(this, function() {
						this.standby(false);
					}));
				}
			}));
		},

		_editObject: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			if (this.moduleFlavor == 'teacher' && items[0].sender != tools.status('username')) {
				// a teacher may only edit his own project
				dialog.alert(_('Only the owner of a project is able to edit its details. If necessary, you are able to transfer the ownership of a project to your account by executing the action "adopt".'));
				return;
			}

			// everything fine, we may edit the project
			this.selectChild(this._detailPage);
			this._detailPage.load(ids[0]);
		},

		_adopt: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			dialog.confirm(_('Please confirm to transfer the ownership of the project "%s" to your account.', items[0].description), [{
				label: _('Cancel'),
				name: 'cancel',
				'default': true
			}, {
				label: _('Adopt project'),
				name: 'adopt'
			}]).then(lang.hitch(this, function(response) {
				if (response === 'adopt') {
					this.standby(true);
					this.umcpCommand('distribution/adopt', ids).then(lang.hitch(this, function(response) {
						this.moduleStore.onChange();
						this.standby(false);

						// prompt any errors to the user
						if (response.result instanceof Array && response.result.length > 0) {
							var res = response.result[0];
							if (!res.success) {
								dialog.alert(_('The following error occurred: %s', res.details));
							}
						}
					}), lang.hitch(this, function() {
						this.moduleStore.onChange();
						this.standby(false);
					}));
				}
			}));
		},

		_delete: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			if (this.moduleFlavor === 'teacher' && items[0].sender != tools.status('username')) {
				// a teacher may only remove his own project
				dialog.alert(_('Only the owner of a project is able to remove it.'));
				return;
			}

			dialog.confirm(_('Please confirm to remove the project: %s', items[0].name), [{
				label: _('Cancel'),
				name: 'cancel',
				'default': true
			}, {
				label: _('Remove project'),
				name: 'remove'
			}]).then(lang.hitch(this, function(response) {
				if (response === 'remove') {
					this.moduleStore.remove(ids[0]);
				}
			}));
		},

		_newObject: function() {
			this.selectChild(this._detailPage);
			this._detailPage.newObject();
		}
	});

});
