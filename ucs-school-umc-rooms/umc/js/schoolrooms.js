/*
 * Copyright 2012-2018 Univention GmbH
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
	"dojo/aspect",
	"umc/dialog",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolrooms/DetailPage",
	"umc/i18n!umc/modules/schoolrooms"
], function(declare, lang, aspect, dialog, ExpandingTitlePane, Grid, Module, Page, SearchForm, SearchBox, ComboBox, DetailPage, _) {

	return declare("umc.modules.schoolrooms", [ Module ], {

		idProperty: '$dn$',
		_grid: null,
		_searchPage: null,
		_detailPage: null,
		_startWithCreation: null, // If set the room creation dialog will be triggered automatically

		buildRendering: function() {
			this.inherited(arguments);
			this.standby(true);

			this._searchPage = new Page({
				fullWidth: true,
				headerText: this.description,
				helpText: ''
			});

			this.addChild(this._searchPage);

			var actions = [{
				name: 'add',
				label: _('Add room'),
				description: _('Create a new room'),
				iconClass: 'umcIconAdd',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_addObject')
			}, {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected object'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}, {
				name: 'delete',
				label: _('Delete'),
				description: _('Deleting the selected objects.'),
				isStandardAction: true,
				isMultiAction: false,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_deleteObjects')
			}];

			var columns = [{
				name: 'name',
				label: _('Name'),
				width: '40%'
			}, {
				name: 'description',
				label: _('Description'),
				width: '60%'
			}];

			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore,
				query: {}
			});

			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				description: _('Choose the school'),
				label: _('School'),
				dynamicValues: 'schoolrooms/schools',
				onDynamicValuesLoaded: lang.hitch(this, function(result) {
					this._detailPage.set('schools', result);
				}),
				autoHide: true
			}, {
				type: SearchBox,
				name: 'pattern',
				description: _('Specifies the substring pattern which is searched for in the displayed name'),
				label: _('Search pattern'),
				inlineLabel: _('Search...'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];

			var layout = [
				[ 'school', 'pattern' ]
			];

			this._searchForm = new SearchForm({
				region: 'top',
				hideSubmitButton: true,
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					// call the grid's filter function
					if (values.school) {
						this._grid.filter(values);
					}
				})
			});

			// turn off the standby animation as soon as all form values have been loaded
			this._searchForm.on('ValuesInitialized', lang.hitch(this, function() {
				this.standby(false);
				var values = this._searchForm.get('value');
				if (values.school) {
					this._grid.filter(values);
				}
				if (this._startWithCreation) {
					this._addObject();
				}
			}));

			this._searchPage.addChild(this._searchForm);
			this._searchPage.startup();

			this._detailPage = new DetailPage({
				moduleStore: this.moduleStore,
				standby: lang.hitch(this, 'standby'),
				standbyDuring: lang.hitch(this, 'standbyDuring')
			});
			this.addChild(this._detailPage);

			this._detailPage.on('close', lang.hitch(this, function() {
				this.selectChild(this._searchPage);
			}));

			this._searchForm.ready().then(lang.hitch(this, function() {
				var handler = aspect.before(this._grid, 'onFilterDone', lang.hitch(this, function(success) {
					//handler.remove();
					if (this._grid.getAllItems().length === 0 && !this._startWithCreation) {
						var title = _('No rooms found');
						var txt = _('No rooms were found.');
						txt += ' ' + _('Would you like to create a room now?');
						dialog.confirm(txt, [{
							name: 'cancel',
							label: _('Cancel')
						}, {
							name: 'add',
							'default': true,
							label: _('Add room')
						}], title).then(lang.hitch(this, function(response) {
							if (response === 'add') {
								this._addObject()
							}
						}));
					}
					return arguments;
				}));
			}));
		},

		_addObject: function() {
			this._detailPage._form.clearFormValues();
			this._detailPage.set('school', this._searchForm.getWidget('school').get('value'));
			this._detailPage.disable('school', false);

			this._detailPage.set('headerText', _('Add room'));
			this._detailPage.set('helpText', _('Create room and assign computers'));
			this.selectChild(this._detailPage);
		},

		_editObject: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}

			this.selectChild(this._detailPage);
			this._detailPage.disable('school', true);
			this._detailPage.set('headerText', _('Edit room'));
			this._detailPage.set('helpText', _('Edit room and assign computers'));
			this._detailPage.load(ids[0]);
		},

		_deleteObjects: function(ids, items) {
			dialog.confirm(lang.replace(_('Should the room {name} be deleted?'), items[0]), [{
				name: 'cancel',
				'default' : true,
				label: _('Cancel')
			}, {
				name: 'delete',
				label: _('Delete')
			}]).then(lang.hitch(this, function(action) {
				if (action != 'delete') {
					return;
				}
				this.standbyDuring(this.moduleStore.remove(ids).then(lang.hitch(this, function(response) {
					if (response.success === true) {
						dialog.alert(_('The room has been deleted successfully'));
					} else {
						dialog.alert(lang.replace(_('The room could not be deleted ({message})'), response));
					}
				})));

			}));
		}
	});

});
