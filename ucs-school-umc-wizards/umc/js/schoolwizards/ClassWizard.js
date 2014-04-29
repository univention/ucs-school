/*
 * Copyright 2012-2014 Univention GmbH
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
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/HiddenInput",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, TextBox, Text, HiddenInput, Wizard, _) {

	return declare("umc.modules.schoolwizards.ClassWizard", [Wizard], {

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
			this.getPage('item').clearNotes();
			this.getPage('item').addNote(message);
		}
	});
});

