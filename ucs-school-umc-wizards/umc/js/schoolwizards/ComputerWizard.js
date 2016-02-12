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
	"umc/tools",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/HiddenInput",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, tools, TextBox, Text, ComboBox, HiddenInput, Wizard, _) {

	return declare("umc.modules.schoolwizards.ComputerWizard", [Wizard], {
		description: _('Create a new computer'),

		getGeneralPage: function() {
			var page = this.inherited(arguments);
			page.widgets.push({
				type: ComboBox,
				name: 'type',
				label: _('Computer type'),
				dynamicValues: 'schoolwizards/computers/types',
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				sortDynamicValues: false
			});
			page.layout.push('type');
			return page;
		},

		getItemPage: function() {
			return {
				name: 'item',
				headerText: this.description,
				helpText: this.editMode ? _('Enter details of the computer.') : _('Enter details to create a new computer.'),
				widgets: [{
					type: TextBox,
					name: 'name',
					label: _('Name'),
					disabled: this.editMode,
					required: true
				}, {
					type: TextBox,
					name: 'ip_address',
					label: _('IP address'),
					required: true
				}, {
					type: TextBox,
					name: 'subnet_mask',
					label: _('Subnet mask'),
					value: '255.255.255.0'
				}, {
					type: TextBox,
					name: 'mac_address',
					label: _('MAC address'),
					required: true
				}, {
					type: TextBox,
					name: 'inventory_number',
					label: _('Inventory number')
				}],
				layout: [
					['name'],
					['ip_address', 'subnet_mask'],
					['mac_address'],
					['inventory_number']
				]
			};
		},

		restart: function() {
			tools.forIn(this.getPage('item')._form._widgets, function(iname, iwidget) {
				iwidget.reset();
			});
			this.inherited(arguments);
		},

		addNote: function() {
			var name = this.getWidget('item', 'name').get('value');
			var message = _('Computer "%s" has been successfully created. Continue to create another computer or press "Cancel" to close this wizard.', name);
			this.getPage('item').clearNotes();
			this.getPage('item').addNote(message);
		}
	});
});

