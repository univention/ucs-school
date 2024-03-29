/*
 * Copyright 2012-2024 Univention GmbH
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
	"dojo/Deferred",
	"dojox/html/entities",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/modules/distribution/DetailPage",
	"umc/i18n!umc/modules/distribution"
], function(declare, lang, Deferred, entities, dialog, tools, Grid, Module, Page, SearchForm, SearchBox, ComboBox, DetailPage, _) {

	var cmpUsername = function(a, b) {
		return a && b && a.toLowerCase() === b.toLowerCase();
	};

	return declare("umc.modules.distribution", [ Module ], {
		idProperty: 'name',
		_grid: null,
		_searchPage: null,
		_detailPage: null,

		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid'
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._searchPage = new Page({
				fullWidth: true
			});
			this.addChild(this._searchPage);

			// define grid actions
			var actions = [{
				name: 'add',
				label: _('Add project'),
				description: _('Create a new distribution project'),
				iconClass: 'plus',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_newObject')
			}, {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected distribution project.'),
				iconClass: 'edit-2',
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
				iconClass: 'trash',
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
				'class': 'umcTextBoxOnBody',
				name: 'filter',
				label: 'Filter',
				staticValues: [
					{ id: 'private', label: _('Only own projects') },
					{ id: 'all', label: _('All projects') }
				]
			}, {
				type: SearchBox,
				'class': 'umcTextBoxOnBody',
				name: 'pattern',
				inlineLabel: _('Search...'),
				description: _('Specifies the substring pattern which is searched for in the projects.'),
				label: _('Search pattern'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];

			var layout = [
				[ 'filter', 'pattern' ]
			];

			this._searchForm = new SearchForm({
				region: 'top',
				hideSubmitButton: true,
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					this._grid.filter(values);
				})
			});

			this._searchPage.addChild(this._searchForm);

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
				dialog.alert(entities.encode(_('Error: No recipients have been assigned to the project!')));
				return;
			}

			var msg = _('Please confirm to collect the project <i>%s</i>.', entities.encode(items[0].description));
			if (!items[0].isDistributed && items[0].files) {
				msg = _('Please confirm to distribute the project <i>%s</i>.', entities.encode(items[0].description));
			} else if (!items[0].isDistributed && !items[0].files) {
				msg = _('Warning: No files have been assigned to the project!<br>Please confirm to distribute the empty project <i>%s</i>.', entities.encode(items[0].description));
			}
			var stepConfirmation = new Deferred();
			dialog.confirm(msg, [{
				label: _('Cancel'),
				callback: function() {stepConfirmation.reject({log: false});}
			}, {
				label: items[0].isDistributed ? _('Collect project') : _('Distribute project'),
				callback: function() {stepConfirmation.resolve();},
				'default': true
			}]);
			stepConfirmation.then(lang.hitch(this, function() {
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
								dialog.contextNotify(_('The project files have been collected successfully.'));
							}
							else {
								dialog.contextNotify(_('The project files have been distributed successfully.'));
							}
						}
					}

					// update the grid if a project has been distributed
					if (!items[0].isDistributed) {
						this.moduleStore.onChange();
					}
				}));
			}));
		},

		_editObject: function(ids, items) {
			if (this.moduleFlavor === 'teacher' && !cmpUsername(items[0].sender, tools.status('username'))) {
				// a teacher may only edit his own project
				dialog.alert(entities.encode(_('Only the owner of a project is able to edit its details. If necessary, you are able to transfer the ownership of a project to your account by executing the action "adopt".')));
				return;
			}

			// everything fine, we may edit the project
			this.selectChild(this._detailPage);
			this._detailPage.load(ids[0]);
		},

		_adopt: function(ids, items) {
			dialog.confirm(_('Please confirm to transfer the ownership of the project <i>%s</i> to your account.', entities.encode(items[0].description)), [{
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
								dialog.alert(entities.encode(_('The following error occurred: %s', res.details)));
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
				dialog.alert(entities.encode(_('Only the owner of a project is able to remove it.')));
				return;
			}

			dialog.confirm(_('Please confirm to remove the project <i>%s</i>.', entities.encode(items[0].description)), [{
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
