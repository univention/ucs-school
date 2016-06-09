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
	"dojo/_base/array",
	"dojo/when",
	"dojo/promise/all",
	"umc/dialog",
	"umc/app",
	"umc/tools",
	"umc/widgets/Wizard",
	"umc/widgets/ComboBox",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, when, all, dialog, UMCApplication, tools, Wizard, ComboBox, _) {

	return declare("umc.modules.schoolwizards.Wizard", [Wizard], {

		umcpCommand: null,
		store: null,

		udmLinkEnabled: null, // flag for showing a link to the fully flegded UDM module
		editMode: null,  // flag for edit mode
		$dn$: null,  // the object we edit
		school: null,  // the school of that object
		objectType: null, // the UDM type of that object
		loadedValues: null, // the values of the object as seen from server

		editModeDescriptionWithoutSchool: _('Edit {itemType} {itemName}'),
		createModeDescriptionWithoutSchool: _('Create a new {itemType}'),
		editModeDescription: _('{itemSchool}: edit {itemType} {itemName}'),
		createModeDescription: _('{itemSchool}: create a new {itemType}'),
		_skippedGeneralPage: false,

		postMixInProperties: function() {
			this.inherited(arguments);
			this.pages = [];
			var generalPage = this.getGeneralPage();
			if (generalPage) {
				this.pages.push(generalPage);
			}
			var itemPage = this.getItemPage();
			this.addUDMLink(itemPage);
			this.pages.push(itemPage);
		},

		addUDMLink: function(page) {
			if (this.udmLinkEnabled && this.editMode && this.objectType && UMCApplication.getModule('udm', 'navigation')) {
				var buttons = page.buttons;
				if (!buttons) {
					buttons = page.buttons = [];
				}
				buttons.push({
					name: 'udm_link',
					label: _('Advanced settings'),
					callback: lang.hitch(this, function() {
						UMCApplication.openModule('udm', 'navigation', {openObject: {objectType: this.objectType, objectDN: this.$dn$}});
						this.onFinished();  // close this wizard
					})
				});
				page.layout.push('udm_link');
			}
		},

		loadVariables: function() {
			return null;
		},

		startup: function() {
			this.inherited(arguments);
			var loading = [this.loadValues(), this.loadVariables()];
			tools.forIn(this._pages, function(name, page) {
				if (page._form) {
					loading.push(page._form.ready());
				}
			});
			loading = all(loading);
			this.standbyDuring(loading);
			when(loading).always(lang.hitch(this, function(values) {
				var name = values && values[0] && values[0].name;
				var _setHandlerAndValue = lang.hitch(this, function(widget, value) {
					if (widget) {
						if (!value && widget.getAllItems) {
							var firstItem = widget.getAllItems()[0];
							value = firstItem && firstItem.id;
						}
						if (value) {
							widget.set('value', value);
							this.setHeader(widget, null, null, value);
						}
						widget.watch('value', lang.hitch(this, 'setHeader', widget));
					}
				});
				var typeWidget = this.getWidget('general', 'type');
				var schoolWidget = this.getWidget('general', 'school');
				var nameWidget = this.getWidget('item', 'name');
				_setHandlerAndValue(typeWidget, this.type);
				_setHandlerAndValue(schoolWidget, this.selectedSchool);
				_setHandlerAndValue(nameWidget, name);
				this.setHeader();
				if (this.selectedSchool && (!typeWidget || this.type)) {
					// hack to go to the next page (itemPage)
					this._skippedGeneralPage = true;
					this._next(this.next(null));
				}
			}));
		},

		hasPrevious: function() {
			if (this.editMode) {
				// make it impossible to show the general page
				return false;
			}
			if (this._skippedGeneralPage) {
				// general page was unnecessary: do not go back!
				return false;
			}
			return this.inherited(arguments);
		},

		setHeader: function(widget, attr, oldVal, newVal) {
			if (widget) {
				if (widget.getAllItems) {
					var allItems = widget.getAllItems();
					array.some(allItems, function(item) {
						if (item.id === newVal) {
							newVal = item.label;
							return true;
						}
					});
				}
				this.set('item' + tools.capitalize(widget.name), newVal);
			}
			var header = null;
			if (this.editMode) {
				if (this.itemSchool) {
					header = lang.replace(this.editModeDescription, {itemSchool: this.itemSchool, itemName: this.itemName, itemType: this.itemType});
				} else {
					header = lang.replace(this.editModeDescriptionWithoutSchool, {itemName: this.itemName, itemType: this.itemType});
				}
			} else {
				if (this.itemSchool) {
					header = lang.replace(this.createModeDescription, {itemSchool: this.itemSchool, itemName: this.itemName, itemType: this.itemType});
				} else {
					header = lang.replace(this.createModeDescriptionWithoutSchool, {itemName: this.itemName, itemType: this.itemType});
				}
			}
			tools.forIn(this._pages, function(name, page) {
				// general page has 'school' and 'type' widget.
				// seems not appropriate to set header to:
				// School: Create new Teacher although you can still
				// change it
				if (page.name != 'general') {
					page.set('headerText', header);
				}
			});
		},

		getGeneralPage: function() {
			return {
				name: 'general',
				headerText: this.description,
				widgets: [{
					name: 'school',
					label: _('School'),
					type: ComboBox,
					staticValues: this.schools,
					value: this.selectedSchool,
					autoHide: true
				}],
				layout: ['school']
			};
		},

		loadValues: function() {
			if (!this.$dn$) {
				return null;
			}
			var load = this.store.get({
				object: {
					$dn$: this.$dn$,
					school: this.school
				}
			});
			load.then(lang.hitch(this, function(result) {
				this.loadedValues = result;
				tools.forIn(result, lang.hitch(this, function(key, value) {
					var widget = this.getWidget(key);
					if (widget) {
						widget.set('value', value);
					}
				}));
			}));
			return load;
		},

		hasNext: function() {
			return true;
		},

		next: function(/*String*/ currentPage) {
			var nextPage = this.inherited(arguments);
			this.updateWidgets(currentPage);
			if (this._getPageIndex(currentPage) === (this.pages.length - 1 )) {
				if (this._validateForm()) {
					if (this.editMode) {
						return this.finishEditMode(currentPage);
					} else {
						return this.finishAddMode(currentPage);
					}
				} else {
					return currentPage;
				}
			}
			return nextPage;
		},

		finishAddMode: function(currentPage) {
			return this._createObject().then(lang.hitch(this, function(result) {
				if (result) {
					this.addNote();
					this.restart();
					this.focusFirstWidget(currentPage);
				}
				return currentPage;
			}));
		},

		finishEditMode: function(currentPage) {
			var values = this.getValues();
			values.$dn$ = this.$dn$;
			values.school = this.school;
			return this.standbyDuring(this.store.put(values)).then(lang.hitch(this, function(response) {
				if (response.result) {
					dialog.alert(response.result.message);
				} else {
					this.onFinished();  // close this wizard
				}
				return currentPage;
			}));
		},

		getFooterButtons: function(pageName) {
			var buttons = this.inherited(arguments);
			if (this._getPageIndex(pageName) === (this.pages.length - 1)) {
				array.forEach(buttons, lang.hitch(this, function(button) {
					if (button.name == 'next') {
						button.label = _('Save');
					}
				}));
			}
			return buttons;
		},

		_validateForm: function() {
			var form = this.selectedChildWidget.get('_form');
			if (!form.validate()) {
				var widgets = form.getInvalidWidgets();
				form.getWidget(widgets[0]).focus();
				return false;
			}
			return true;
		},

		_createObject: function() {
			var values = this.getValues();
			return this.standbyDuring(this.store.add(values)).then(
				function(response) {
					if (response.result) {
						dialog.alert(response.result.message);
						return false;
					}
					return true;
				},
				function() {
					return false;
				}
			);
		},

		restart: function() {
		},

		updateWidgets: function(/*String*/ currentPage) {
		},

		focusFirstWidget: function(pageName) {
			// Determine the name of the first widget
			var layout = this.getPage(pageName)._form.get('layout');
			while (layout instanceof Array) {
				layout = layout[0];
			}
			this.getWidget(pageName, layout).focus();
		}
	});
});
