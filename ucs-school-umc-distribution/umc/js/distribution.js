/*
 * Copyright 2012-2016 Univention GmbH
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
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/distribution/DetailPage",
	"umc/i18n!umc/modules/distribution"
], function(declare, lang, dialog, tools, Grid, Module, Page, SearchForm, TextBox, ComboBox, DetailPage, _) {

	var cmpUsername = function(a, b) {
		return a && b && a.toLowerCase() == b.toLowerCase();
	};

	return declare("umc.modules.distribution", [ Module ], {
		idProperty: 'name',
		_grid: null,
		_searchPage: null,
		_detailPage: null,

		postMixInProperties: function() {
			this.inherited(arguments);
			this.standbyOpacity = 1;
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._searchPage = new Page({
				headerText: this.description,
				helpText: ''
			});
			this.addChild(this._searchPage);

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
				description: _('Edit the selected distribution project.'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}, {
				name: 'distribute',
				label: _('Distribute'),
				description: _('Distribute project files to users.'),
				isStandardAction: true,
				isMultiAction: false,
				canExecute: function(item) {
					return !item.isDistributed;
				},
				callback: lang.hitch(this, '_distribute')
			}, {
				name: 'collect',
				label: _('Collect'),
				description: _('Collect project files from users.'),
				isStandardAction: true,
				isMultiAction: false,
				canExecute: function(item) {
					return item.isDistributed;
				},
				callback: lang.hitch(this, '_distribute')
			}, {
				name: 'adopt',
				label: _('Adopt'),
				canExecute: function(item) {
					return !cmpUsername(item.sender, tools.status('username'));
				},
				description: _('Transfer the ownership of the selected project to your account.'),
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_adopt')
			}, {
				name: 'remove',
				label: _('Remove'),
				description: _('Removes the project from the internal database.'),
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

			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore,
				query: { pattern: '' }
			});

			this._searchPage.addChild(this._grid);

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
				description: _('Specifies the substring pattern which is searched for in the projects.'),
				label: _('Search pattern')
			}];

			var layout = [
				[ 'filter', 'pattern', 'submit' ]
			];

			this._searchForm = new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					this._grid.filter(values);
				})
			});

			this._searchPage.addChild(this._searchForm);

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
			if (!items[0].recipients) {
				// no recipients have been added to project, abort
				dialog.alert(_('Error: No recipients have been assigned to the project!'));
				return;
			}

			if (!items[0].files) {
				// no files have been added to project, abort
				dialog.alert(_('Error: No files have been assign to the project!'));
				return;
			}

			var msg = items[0].isDistributed ?
				_('Please confirm to collect the project <i>%s</i>.', items[0].description) :
				_('Please confirm to distribute the project <i>%s</i>.', items[0].description);
			dialog.confirm(msg, [{
				label: _('Cancel'),
				name: 'cancel'
			}, {
				label: items[0].isDistributed ? _('Collect project') : _('Distribute project'),
				name: 'doit',
				'default': true
			}]).then(lang.hitch(this, function(response) {
				if (response === 'doit') {
					// collect or distribute the project, according to its current state
					var cmd = items[0].isDistributed ? 'distribution/collect' : 'distribution/distribute';
					this.standbyDuring(this.umcpCommand(cmd, ids)).then(lang.hitch(this, function(response) {
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
					}));
				}
			}));
		},

		_editObject: function(ids, items) {
			if (this.moduleFlavor == 'teacher' && !cmpUsername(items[0].sender, tools.status('username'))) {
				// a teacher may only edit his own project
				dialog.alert(_('Only the owner of a project is able to edit its details. If necessary, you are able to transfer the ownership of a project to your account by executing the action "adopt".'));
				return;
			}

			// everything fine, we may edit the project
			this.selectChild(this._detailPage);
			this._detailPage.load(ids[0]);
		},

		_adopt: function(ids, items) {
			dialog.confirm(_('Please confirm to transfer the ownership of the project <i>%s</i> to your account.', items[0].description), [{
				label: _('Cancel'),
				name: 'cancel',
				'default': true
			}, {
				label: _('Adopt project'),
				name: 'adopt'
			}]).then(lang.hitch(this, function(response) {
				if (response === 'adopt') {
					this.standbyDuring(this.umcpCommand('distribution/adopt', ids)).then(lang.hitch(this, function(response) {
						this.moduleStore.onChange();

						// prompt any errors to the user
						if (response.result instanceof Array && response.result.length > 0) {
							var res = response.result[0];
							if (!res.success) {
								dialog.alert(_('The following error occurred: %s', res.details));
							}
						}
					}), lang.hitch(this, function() {
						this.moduleStore.onChange();
					}));
				}
			}));
		},

		_delete: function(ids, items) {
			if (this.moduleFlavor === 'teacher' && !cmpUsername(items[0].sender, tools.status('username'))) {
				// a teacher may only remove his own project
				dialog.alert(_('Only the owner of a project is able to remove it.'));
				return;
			}

			dialog.confirm(_('Please confirm to remove the project <i>%s</i>.', items[0].description), [{
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
