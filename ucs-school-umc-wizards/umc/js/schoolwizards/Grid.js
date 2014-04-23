/*
 * Copyright 2014 Univention GmbH
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
], function(declare, lang, array, topic, query, tools, dialog, store, Grid, Text, Page, StandbyMixin, SearchForm, ExpandingTitlePane, _) {

	return declare("umc.modules.schoolwizards.Grid", [Page, StandbyMixin], {

		module: null,
		umcpCommand: null,
		moduleFlavor: null,
		idProperty: '$dn$',

		buildRendering: function() {
			this.inherited(arguments);

			var titlePane = this.getTitlePane();
			this.addChild(titlePane);

			this._grid = this.getGrid();

			this._searchForm = this.getSearchForm();
			titlePane.addChild(this._grid);
			titlePane.addChild(this._searchForm);
		},

		startup: function() {
			this.inherited(arguments);
			this._grid.resize();
		},

		getSelectedSchool: function() {
			var school = this._searchForm.getWidget('school');
			if (school) {
				return school.get('value');
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
				standbyDuring: lang.hitch(this, 'standbyDuring')
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

		getSearchForm: function() {
			var widgets = this.getSearchWidgets();
			var buttons = this.getSearchButtons();
			var layout = this.getSearchLayout();

			return new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: layout,
				buttons: buttons,
				onSearch: lang.hitch(this, 'filter')
			});
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
			this._grid.filter(props);
		},

		createObject: function() {
			this.createWizard({
				editMode: false,
				$dn$: null,
				objectType: null
			});
		},

		editObjects: function(ids, items) {
			this.createWizard({
				editMode: true,
				$dn$: items[0].$dn$,
				objectType: items[0].objectType
			});
		},

		createWizard: function(props) {
			var wizard = new this.createObjectWizard(lang.mixin({
				description: this.description,
				store: this._grid.moduleStore,
				school: this.getSelectedSchool(),
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
			var msg = _('Please confirm to delete the %d selected %s!', objects.length, this.objectNamePlural);
			if (objects.length == 1) {
				msg = _('Please confirm to delete %s %s', this.objectNameSingular, this.getObjectIdName(objects[0]));
			}
			return msg;
		},

		confirmObjectDeletion: function(ids, objects) {
			dialog.confirmForm({
				widgets: [{
					type: Text,
					label: '',
					name: 'text',
					content: '<p>' + this.getDeleteConfirmMessage(objects) + '</p>'
				}],
				submit: _('Delete')
			}).then(lang.hitch(this, function() {
				return this.deleteObjects(ids, objects);
			}));
		},

		deleteObjects: function(ids, objects) {
			// TODO: notifications
			array.forEach(objects, lang.hitch(this, function(object) {
				this._grid.moduleStore.remove({
					$dn$: object.$dn$,
					school: object.school
				});
			}));
		}
	});
});
