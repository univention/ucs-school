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
	"umc/tools",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/HiddenInput",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, tools, TextBox, ComboBox, HiddenInput, Wizard, _) {

	return declare("umc.modules.schoolwizards.ComputerWizard", [Wizard], {

		postMixInProperties: function() {
			this.inherited(arguments);
			this.pages = this.getPages();
		},

		startup: function() {
			this.inherited(arguments);
			if (this.editMode) {
				this.loadingDeferred.always(lang.hitch(this, function() {
					// hack to go to the next page
					this._next(this.next(null));
				}));
			}
		},

		hasPrevious: function() {
			if (this.editMode) {
				// make it impossible to show the general page
				return false;
			}
			return this.inherited(arguments);
		},

		getPages: function() {
			var general = this.getGeneralPage();
			var computer = this.getComputerPage();
			return [general, computer];
		},

		getGeneralPage: function() {
			return {
				name: 'general',
				headerText: this.description,
				helpText: _('Specify the computer type.'),
				widgets: [{
					name: 'school',
					type: HiddenInput,
					value: this.school
				}, {
					type: ComboBox,
					name: 'type',
					label: _('Type'),
					dynamicValues: 'schoolwizards/computers/types',
					umcpCommand: lang.hitch(this, 'umcpCommand'),
					sortDynamicValues: false
				}],
				layout: [['school'], ['type']]
			};
		},

		getComputerPage: function() {
			return {
				name: 'computer',
				headerText: this.description,
				helpText: this.editMode ? _('Enter details of the computer.') : _('Enter details to create a new computer.'),
				widgets: [{
					type: TextBox,
					name: 'name',
					label: _('Name'),
					required: true
				}, {
					type: TextBox,
					name: 'ipAddress',
					label: _('IP address'),
					required: true
				}, {
					type: TextBox,
					name: 'subnetMask',
					label: _('Subnet mask'),
					value: '255.255.255.0'
				}, {
					type: TextBox,
					name: 'mac',
					label: _('MAC address'),
					required: true
				}, {
					type: TextBox,
					name: 'inventoryNumber',
					label: _('Inventory number')
				}],
				layout: [
					['name'],
					['ipAddress', 'subnetMask'],
					['mac'],
					['inventoryNumber']
				]
			};
		},

		restart: function() {
			tools.forIn(this.getPage('computer')._form._widgets, function(iname, iwidget) {
				iwidget.reset();
			});
			this.inherited(arguments);
		},

		addNote: function() {
			var name = this.getWidget('computer', 'name').get('value');
			var message = _('Computer "%s" has been successfully created. Continue to create another computer or press "Cancel" to close this wizard.', name);
			this.getPage('computer').clearNotes();
			this.getPage('computer').addNote(message);
		}
	});
});
