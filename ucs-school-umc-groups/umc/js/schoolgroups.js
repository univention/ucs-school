/*
 * Copyright 2012-2015 Univention GmbH
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
	"umc/widgets/Module",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/SearchForm",
	"umc/modules/schoolgroups/DetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, dialog, Module, Grid, Page, TextBox, ComboBox, SearchForm, DetailPage, _) {

	return declare("umc.modules.schoolgroups", [Module], {
		idProperty: '$dn$',
		_grid: null,
		_searchPage: null,
		_detailPage: null,
		standbyOpacity: 1,

		buildRendering: function() {
			this.inherited(arguments);

			this.standby(true);

			this._searchPage = new Page({
				headerText: this.description,
				helpText: ''
			});

			this.addChild(this._searchPage);

			var actions = [{
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected object'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}];

			// only workgroups can be deleted or added
			if (this.moduleFlavor == 'workgroup-admin') {
				actions.push({
					name: 'add',
					label: _('Add workgroup'),
					description: _('Create a new workgroup'),
					iconClass: 'umcIconAdd',
					isContextAction: false,
					isStandardAction: true,
					callback: lang.hitch(this, '_addObject')
				});
				actions.push({
					name: 'delete',
					label: _('Delete'),
					description: _('Deleting the selected objects.'),
					isStandardAction: true,
					isMultiAction: false,
					iconClass: 'umcIconDelete',
					callback: lang.hitch(this, '_deleteObjects')
				});
			}

			var columns = [{
				name: 'name',
				label: _('Name'),
				width: '20%'
			}, {
				name: 'description',
				label: _('Description'),
				width: 'auto'
			}];

			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore
			});

			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				dynamicValues: 'schoolgroups/schools',
				label: _('School'),
				size: 'TwoThirds',
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				onDynamicValuesLoaded: lang.hitch(this, function(result) {
					this._detailPage.set('schools', result);
				}),
				autoHide: true
			}, {
				type: TextBox,
				name: 'pattern',
				size: 'TwoThirds',
				description: _('Specifies the substring pattern which is searched for in the displayed name'),
				label: _('Search pattern')
			}];

			this._searchForm = new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: [
					['school', 'pattern', 'submit']
				],
				onSearch: lang.hitch(this, function(values) {
					if (values.school) {
						this._grid.filter(values);
					}
				}),
				onValuesInitialized: lang.hitch(this, function() {
					this.standby(false);
					this.standbyOpacity = 0.75;
					var values = this._searchForm.get('value');
					if (values.school) {
						this._grid.filter(values);
					}
			 	 })
			});

			this._searchPage.addChild(this._searchForm);

			this._searchPage.startup();

			this._detailPage = new DetailPage({
				moduleStore: this.moduleStore,
				moduleFlavor: this.moduleFlavor
			});
			this.addChild(this._detailPage);

			// connect to the onClose event of the detail page... we need to manage
			// visibility of sub pages here
			this._detailPage.on('close', lang.hitch(this, function() {
				this.selectChild(this._searchPage);
			}));
		},

		_addObject: function() {
			this._detailPage._form.clearFormValues();

			this._detailPage.set('headerText', _('Add workgroup'));
			this._detailPage.set('school', this._searchForm.getWidget('school').get('value'));
			this._detailPage.disableFields(false);
			this.selectChild(this._detailPage);
		},

		_editObject: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			this._detailPage.disableFields(true);
			if (this.moduleFlavor === 'class') {
				this._detailPage.set('headerText', _('Edit class'));
			} else {
				this._detailPage.set('headerText', _('Edit workgroup'));
			}
			this.selectChild(this._detailPage);
			this._detailPage.load(ids[0]);
		},

		_deleteObjects: function(ids, items) {
			dialog.confirm(lang.replace(_('Should the workgroup {name} be deleted?'), items[0]), [{
				name: 'cancel',
				'default' : true,
				label: _('Cancel')
			}, {
				name: 'delete',
				label: _('Delete')
			}]).then(lang.hitch(this, function(action) {
				if (action != 'delete') {
					// action canceled
					return;
				}
				this.standbyDuring(this.moduleStore.remove(ids)).then(lang.hitch(this, function(response) {
					if (response.success === true) {
						dialog.alert(_('The workgroup has been deleted successfully'));
					} else {
						dialog.alert(lang.replace(_('The workgroup could not be deleted ({message})'), response));
					}
				}));
			}));
		}
	});
});
