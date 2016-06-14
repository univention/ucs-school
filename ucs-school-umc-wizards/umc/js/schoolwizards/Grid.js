/*
 * Copyright 2014-2016 Univention GmbH
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
	"dojo/topic",
	"dojo/query",
	"dojo/aspect",
	"umc/tools",
	"umc/dialog",
	"umc/store",
	"umc/widgets/Grid",
	"umc/widgets/Text",
	"umc/widgets/Page",
	"umc/widgets/StandbyMixin",
	"umc/widgets/SearchForm",
	"umc/widgets/ExpandingTitlePane",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, topic, query, aspect, tools, dialog, store, Grid, Text, Page, StandbyMixin, SearchForm, ExpandingTitlePane, _) {

	return declare("umc.modules.schoolwizards.Grid", [Page, StandbyMixin], {

		autoSearch: true,
		udmLinkEnabled: null,
		module: null,
		umcpCommand: null,
		moduleFlavor: null,
		sortFields: ['school', 'name'],
		idProperty: '$dn$',

		buildRendering: function() {
			this.inherited(arguments);

			var titlePane = this.getTitlePane();
			this.addChild(titlePane);

			this._grid = this.getGrid();

			this.buildSearchForm();
			titlePane.addChild(this._grid);
			titlePane.addChild(this._searchForm);
		},

		startup: function() {
			this.inherited(arguments);
			this._grid.resize();
		},

		getSelectedSchool: function() {
			var widget = this._searchForm.getWidget('school');
			if (widget) {
				var val = widget.get('value');
				if (val == '/') {
					val = '';
				}
				return val;
			}
		},

		getSelectedType: function() {
			var widget = this._searchForm.getWidget('type');
			if (widget) {
				var val = widget.get('value');
				if (val == 'all') {
					val = '';
				}
				return val;
			}
		},

		getTitlePane: function() {
			return new ExpandingTitlePane({
				title: _('Search for %s', this.objectNamePlural),
				design: 'sidebar'
			});
		},

		getGrid: function() {
			var grid = new Grid({
				region: 'center',
				footerFormatter: lang.hitch(this, 'getGridFooter'),
				defaultAction: this.getGridDefaultAction(),
				actions: this.getGridActions(),
				columns: this.getGridColumns(),
				moduleStore: this.getGridStore(),
				sortIndex: null,
				standbyDuring: lang.hitch(this, 'standbyDuring')
			});
			// when using All schools, sort by school, name
			grid._grid.sortFields = array.map(this.sortFields, function(field) {
				return {
					attribute: field,
					descending: false
				};
			});

			// Add horizontal scrollbar
			//query('.dojoxGridScrollbox', grid.domNode).style('overflowX', 'auto');
			return grid;
		},

		getGridDefaultAction: function() {
			return 'edit';
		},

		getGridActions: function() {
			return [this.getGridAddAction(), this.getGridEditAction(), this.getGridDeleteAction()];
		},

		getGridAddAction: function() {
			return {
				name: 'add',
				label: _('Add'),
				description: _('Add a new %s', this.objectNameSingular),
				iconClass: 'umcIconAdd',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, 'createObject')
			};
		},

		getGridEditAction: function() {
			return {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the %s.', this.objectNameSingular),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, 'editObjects')
			};
		},

		getGridDeleteAction: function() {
			return {
				name: 'delete',
				label: _('Delete'),
				description: _('Deleting the selected %s.', this.objectNamePlural),
				isStandardAction: true,
				isMultiAction: true,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, 'confirmObjectDeletion')
			};
		},

		getGridColumnsWithSchool: function() {
			var columns = [];
			if (this.getSelectedSchool() === '') {
				columns.push({
					name: 'school',
					label: _('School')
				});
			}
			columns = this.getGridColumns().concat(columns);
			return columns;
		},

		getGridColumns: function() {
			return [];
		},

		getGridStore: function() {
			var s = store(this.idProperty, this.basePath || this.moduleFlavor, this.moduleFlavor);
			s.umcpCommand = lang.hitch(this, 'umcpCommand');
			return s;
		},

		getGridFooter: function(nItems, nItemsTotal) {
			var map = {
				nSelected: nItems,
				nTotal: nItemsTotal,
				objPlural: this.objectNamePlural,
				objSingular: this.objectNameSingular
			};
			if (0 === nItemsTotal) {
				return _('No %(objPlural)s could be found', map);
			} else if (1 == nItems) {
				return _('%(nSelected)d %(objSingular)s of %(nTotal)d selected', map);
			} else {
				return _('%(nSelected)d %(objPlural)s of %(nTotal)d selected', map);
			}
		},

		buildSearchForm: function() {
			var widgets = this.getSearchWidgets();
			var buttons = this.getSearchButtons();
			var layout = this.getSearchLayout();

			this._searchForm = new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: layout,
				buttons: buttons,
				onSearch: lang.hitch(this, 'filter')
			});
			if (this.autoSearch) {
				this._searchForm.ready().then(lang.hitch(this, function() {
					this.filter({type: 'all'});
					if (!this.schools.length) {
						return;
					}
					var handler = aspect.before(this._grid._grid, '_onFetchComplete', lang.hitch(this, function(items) {
						handler.remove();
						if (items.length === 0) {
							var title = _('No %(objectNamePlural)s found', {objectNamePlural: this.objectNamePlural});
							var txt = _('No %(objectNamePlural)s were found.', {objectNamePlural: this.objectNamePlural});
							txt += ' ' + _('Would you like to create %(firstObject)s now?', {firstObject: this.firstObject});
							dialog.confirm(txt, [{
								name: 'cancel',
								label: _('Cancel')
							}, {
								name: 'add',
								'default': true,
								label: _('Create')
							}], title).then(lang.hitch(this, function(response) {
								if (response == 'add') {
									this.createObject();
								}
							}));
						}
						return arguments;
					}));
				}));
			}
		},

		getSearchButtons: function() {
			return [{
				name: 'submit',
				label: _('Search')
			}];
		},

		getSearchLayout: function() {
			return null;
		},

		getSearchWidgets: function() {
			return [];
		},

		filter: function(props) {
			props.school = this.getSelectedSchool();
			this._grid.filter(props);
			this._grid.set('columns', this.getGridColumnsWithSchool());
		},

		createObject: function() {
			this.createWizard({
				editMode: false,
				$dn$: null,
				school: this.getSelectedSchool(),
				selectedSchool: this.getSelectedSchool(),
				type: this.getSelectedType(),
				itemType: tools.capitalize(this.objectNameSingular),
				objectType: null
			});
		},

		editObjects: function(ids, items) {
			var item = items[0];
			this.createWizard({
				editMode: true,
				$dn$: item.$dn$,
				school: item.school,
				selectedSchool: item.schools ? this.getSelectedSchool(): item.school,  // User with multiple schools must have the view of the currently selected school!
				type: item.type,
				itemType: tools.capitalize(this.objectNameSingular),
				objectType: item.objectType
			});
		},

		createWizard: function(props) {
			var wizard = new this.createObjectWizard(lang.mixin({
				udmLinkEnabled: this.udmLinkEnabled,
				store: this._grid.moduleStore,
				schools: this.schools,
				umcpCommand: lang.hitch(this, 'umcpCommand')
			}, props));
			this.module.addChild(wizard);
			this.module.selectChild(wizard);
			var closeWizard = lang.hitch(this, function() {
				this.module.selectChild(this);
				this.module.removeChild(wizard);
			});
			wizard.on('cancel', closeWizard);
			wizard.on('finished', closeWizard);

			// TODO: test if still works... why does it exists?
			if (!props.editMode && 'onShow' in wizard) {
				// send a reload command to wizard
				this.module.on('show', lang.hitch(this, function(evt) {
					wizard.onShow();
				}));
			}
		},

		getObjectIdName: function(item) {
			return '';
		},

		getDeleteConfirmMessage: function(objects) {
			var msg = _('Please confirm to delete the %(num)d selected %(objectNamePlural)s.', {num: objects.length, objectNamePlural: this.objectNamePlural});
			if (objects.length == 1) {
				msg = _('Please confirm to delete %(objectNameSingular)s "%(objectName)s".', {objectNameSingular: this.objectNameSingular, objectName: this.getObjectIdName(objects[0])});
			}
			return msg;
		},

		confirmObjectDeletion: function(ids, objects) {
			dialog.confirm('<p>' + this.getDeleteConfirmMessage(objects) + '</p>',
				[{
				name: 'cancel',
				'default': true,
				label: _('Cancel')
			}, {
				name: 'delete',
				label: _('Delete')
			}]).then(lang.hitch(this, function(response) {
				if (response == 'delete') {
					this.deleteObjects(ids, objects);
				}
			}));
		},

		deleteObjects: function(ids, objects) {
			var transaction = this._grid.moduleStore.transaction();
			array.forEach(objects, function(object) {
				this._grid.moduleStore.remove({
					$dn$: object.$dn$,
					school: object.schools ? this.school : object.school  // if it's a user on multiple schools we need to remove him only from one school -> send the selected school
				});
			}, this);
			return this.standbyDuring(transaction.commit()).then(
				function(response) {
					var errorMessages = [];
					array.forEach(response, function(res) {
						if (res.result) {
							errorMessages.push(res.result.message);
						}
					});
					if (errorMessages.length) {
						dialog.alert(errorMessages.join(' '));
						return false;
					}
					return true;
				},
				function() {
					return false;
				}
			);
		}
	});
});
