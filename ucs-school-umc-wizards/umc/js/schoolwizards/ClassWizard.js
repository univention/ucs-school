/*
 * SPDX-FileCopyrightText: 2012-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */

/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/dialog",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/HiddenInput",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, dialog, TextBox, Text, HiddenInput, Wizard, _) {

	return declare("umc.modules.schoolwizards.ClassWizard", [Wizard], {
		description: _('Create a new class'),

		getItemPage: function() {
			return {
				name: 'item',
				helpText: this.editMode ? _('Enter details of the class.') : _('Enter details to create a new class.'),
				widgets: [{
					type: TextBox,
					name: 'name',
					label: _('Name'),
					required: true
				}, {
					type: TextBox,
					name: 'description',
					label: _('Description')
				}, {
				}],
				layout: [['name', 'description']]
			};
		},

		restart: function() {
			this.getWidget('item', 'name').reset();
			this.getWidget('item', 'description').reset();
			this.inherited(arguments);
		},

		addNote: function() {
			var name = this.getWidget('item', 'name').get('value');
			var message = _('Class "%s" has been successfully created. Continue to create another class or press "Cancel" to close this wizard.', name);
			dialog.contextNotify(message);
		}
	});
});

