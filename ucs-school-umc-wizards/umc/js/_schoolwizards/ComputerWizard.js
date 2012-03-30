/*
 * Copyright 2012 Univention GmbH
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

/*global console MyError dojo dojox dijit umc */

dojo.provide("umc.modules._schoolwizards.ComputerWizard");

dojo.require("umc.dialog");
dojo.require("umc.i18n");

dojo.require("umc.modules._schoolwizards.Wizard");

dojo.declare("umc.modules._schoolwizards.ComputerWizard", [ umc.modules._schoolwizards.Wizard, umc.i18n.Mixin ], {

	createObjectCommand: 'schoolwizards/computers/create',

	constructor: function() {
		this.pages = [{
			name: 'general',
			headerText: this._('General information'),
			helpText: this._('Here\'s a simple helpText'),
			widgets: [{
				type: 'ComboBox',
				name: 'school',
				label: this._('School'),
				dynamicValues: 'schoolwizards/schools',
				autoHide: true
			}, {
				type: 'ComboBox',
				name: 'type',
				label: this._('Type'),
				// TODO: which types?
				staticValues: [{
					id: 'ipmanagedclient',
					label: this._('ipmanagedclient')
				}, {
					id: 'macos',
					label: this._('macos')
				}, {
					id: 'managedclient',
					label: this._('managedclient')
				}, {
					id: 'memberserver',
					label: this._('memberserver')
				}, {
					id: 'mobileclient',
					label: this._('mobileclient')
				}, {
					id: 'thinclient',
					label: this._('thinclient')
				}, {
					id: 'windows',
					label: this._('windows')
				}]
			}],
			layout: [['school'], ['type']]
		}, {
			name: 'computer',
			headerText: this._('Computer information'),
			helpText: this._('Here\'s a simple helpText'),
			widgets: [{
				type: 'TextBox',
				name: 'name',
				label: this._('Name'),
				required: true
			}, {
				type: 'TextBox',
				name: 'ipAddress',
				label: this._('IP-Address'),
				required: true
			}, {
				type: 'TextBox',
				name: 'subnetMask',
				label: this._('Subnetmask')
			}, {
				type: 'TextBox',
				name: 'mac',
				label: this._('MAC-Address'),
				required: true
			}, {
				type: 'TextBox',
				name: 'inventoryNumber',
				label: this._('Inventory number')
			}],
			layout: [['name'],
			         ['ipAddress', 'subnetMask'],
			         ['mac'],
			         ['inventoryNumber']]
		}, {
			name: 'finish',
			headerText: this._('Finished'),
			helpText: this._('Here\'s a simple helpText')
		}];
	}
});
