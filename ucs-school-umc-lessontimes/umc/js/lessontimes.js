/*
 * SPDX-FileCopyrightText: 2012-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojox/html/entities",
	"umc/dialog",
	"umc/widgets/Form",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/MultiInput",
	"umc/widgets/TextBox",
	"umc/widgets/TimeBox",
	"umc/i18n!umc/modules/lessontimes"
], function(declare, lang, entities, dialog, Form, Module, Page, MultiInput, TextBox, TimeBox, _) {

	return declare("umc.modules.lessontimes", [ Module ], {

		buildRendering: function() {
			this.inherited(arguments);

			this.standby(true);
			this.umcpCommand('lessontimes/get').then(lang.hitch(this, function(response) {
				this.renderPage(response.result);
			}));
		},

		renderPage: function(values) {
			var widgets = [{
				type: MultiInput,
				name: 'lessons',
				label: _(''),
				subtypes: [{
					type: TextBox,
					name: 'description',
					label: _('Description'),
					size: 'TwoThirds'
				}, {
					type: TimeBox,
					name: 'begin',
					label: _('Start time'),
					size: 'TwoThirds'
				}, {
					type: TimeBox,
					name: 'end',
					label: _('End time'),
					size: 'TwoThirds'
				}],
				value: values
			}];

			var layout = [{
				label: _('Lesson times'),
				layout: ['lessons']
			}];

			this._form = new Form({
				widgets: widgets,
				layout: layout
			});

			// turn off the standby animation as soon as all form values have been loaded
			this._form.on('ValuesInitialized', lang.hitch(this, function() {
				this.standby(false);
			}));

			var buttons = [{
				name: 'submit',
				label: _('Submit'),
				'default': true,
				callback: lang.hitch(this, function() {
					var values = this._form.get('value');
					this.onSubmit(values);
				})
			}];

			this._page = new Page({
				headerText: this.description,
				helpText: _('The lesson times are used internally for the default session duration by the computer room module. It is advisable to set the end time of a lesson to a time immediately before the beginning of the following lesson.'),
				headerButtons: buttons
			});
			this.addChild(this._page);

			this._page.addChild(this._form);
		},

		onSubmit: function(values) {
			this.standbyDuring(this.umcpCommand('lessontimes/set', values)).then(lang.hitch(this, function(response) {
				if (response.result.message) {
					dialog.alert(entities.encode(response.result.message));
				}
			}));
		}
	});
});
