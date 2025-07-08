/*
 * SPDX-FileCopyrightText: 2011-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/StandbyMixin",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiObjectSelect",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, array, Page, Form, StandbyMixin, TextBox, ComboBox, MultiObjectSelect, _) {

	return declare("umc.modules.schoolgroups.DetailPage", [ Page, StandbyMixin ], {
		mainContentClass: 'umcCard2', // umc/widgets/Page.js

		moduleStore: null,
		moduleFlavor: null,
		umcpCommand: null,
		_form: null,

		multiWidgetName: 'members',

		postMixInProperties: function() {
			this.inherited(arguments);

			// configure buttons for the header of the detail page, overwriting
			// the "close" button
			this.headerButtons = [{
				name: 'submit',
				label: _('Save changes'),
				iconClass: 'save',
				callback: lang.hitch(this, '_save')
			}, {
				name: 'close',
				label: _('Back to overview'),
				iconClass: 'arrow-left',
				callback: lang.hitch(this, 'onClose')
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._form = new Form({
				widgets: this.getWidgets(),
				moduleStore: this.moduleStore
			});
			this.addChild(this._form);

			this._form.getWidget(this.multiWidgetName).on('ShowDialog', lang.hitch(this, function(_dialog) {
				// if the school changed in the WorkgroupDetailPage, change it also in the dialog and
				// remove all cached users from the store
				var dialogSchool = _dialog._form.getWidget('school');
				var detailPageSchool = this._form.getWidget('school');
				if (dialogSchool.get('value') !== detailPageSchool.get('value')) {
					_dialog._multiSelect._clearValues();
				}
				dialogSchool.setInitialValue(detailPageSchool.get('value'));
			}));

			this._form.on('submit', lang.hitch(this, '_save'));
		},

		getWidgets: function() {
			return [];
		},

		getMultiSelectWidget: function() {
			return {
				type: MultiObjectSelect,
				name: this.multiWidgetName,
				queryWidgets: array.filter([{
					type: ComboBox,
					name: 'school',
					visible: false,
					label: _('School'),
					dynamicValues: 'schoolgroups/schools',
					umcpCommand: lang.hitch(this, 'umcpCommand'),
					autoHide: false
				}, this.getMultiSelectGroup(), {
					type: TextBox,
					name: 'pattern',
					label: _('Name')
				}], function(i) { return i; }),
				queryCommand: lang.hitch(this, function(options) {
					return this.umcpCommand('schoolgroups/users', options).then(function(data) {
						return data.result;
					});
				}),
				queryOptions: function() { return {}; },
				autoSearch: false
			};
		},

		getMultiSelectGroup: function() {
			return {
				type: ComboBox,
				name: 'group',
				label: _('User group or class'),
				depends: 'school',
				selectFirstValueInListIfValueIsInvalidAfterLoadingValues: true,
				dynamicValues: 'schoolgroups/classes',
				umcpCommand: lang.hitch(this, 'umcpCommand')
			};
		},

		_save: function() {
			var values = this._form.get('value');
			var deferred = null;
			var nameWidget = this._form.getWidget('name');

			if (!this._form.validate()) {
				nameWidget.focus();
				return;
			}

			if (values.$dn$) {
				deferred = this.moduleStore.put(values);
			} else {
				deferred = this.moduleStore.add(values);
			}

			deferred.then(lang.hitch(this, function() {
				this.onClose();
			}));
		},

		disableFields: function(disable) {
			this._form.getWidget('school').set('disabled', disable);
			this._form.getWidget('name').set('disabled', disable);
		},

		setupEditMode: function() {

		},

		_setSchoolAttr: function(school) {
			this._form.getWidget('school').set('value', school);
		},

		_setSchoolsAttr: function(schools) {
			var school = this._form.getWidget('school');
			school.set('staticValues', schools);
			school.set('visible', schools.length > 1);
		},

		loadDeferred: null,
		load: function(id) {
			// this._form.getWidget('name').setValid(null);
			this.loadDeferred = this._form.load(id);
			return this.standbyDuring(this.loadDeferred);
		},

		onClose: function(dn, objectType) {
			// event stub
		}
	});

});
