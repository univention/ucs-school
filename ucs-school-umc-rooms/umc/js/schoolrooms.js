/*
 * SPDX-FileCopyrightText: 2012-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/aspect",
	"dojox/html/entities",
	"umc/dialog",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolrooms/DetailPage",
	"umc/i18n!umc/modules/schoolrooms"
], function(declare, lang, aspect, entities, dialog, Grid, Module, Page, SearchForm, SearchBox, ComboBox, DetailPage, _) {

	return declare("umc.modules.schoolrooms", [ Module ], {

		idProperty: '$dn$',
		_grid: null,
		_searchPage: null,
		_detailPage: null,
		_startWithCreation: null, // If set the room creation dialog will be triggered automatically

		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid'
		},

		buildRendering: function() {
			this.inherited(arguments);
			this.standby(true);

			this._searchPage = new Page({
				fullWidth: true
			});

			this.addChild(this._searchPage);

			var actions = [{
				name: 'add',
				label: _('Add room'),
				description: _('Create a new room'),
				iconClass: 'plus',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_addObject')
			}, {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected object'),
				iconClass: 'edit-2',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}, {
				name: 'delete',
				label: _('Delete'),
				description: _('Deleting the selected objects.'),
				isStandardAction: true,
				isMultiAction: false,
				iconClass: 'trash',
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
				allowHTML: false,
				query: {}
			});

			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
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
				'class': 'umcTextBoxOnBody',
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
			dialog.confirm(lang.replace(_('Should the room {name} be deleted?'), {name: entities.encode(items[0].name)}), [{
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
						dialog.alert(lang.replace(_('The room could not be deleted ({message})'), {message: entities.encode(response.message)}));
					}
				})));

			}));
		}
	});
});
