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
			helpText: this._('This module creates a new computer on the system.'),
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
				staticValues: [{
					id: 'ipmanagedclient',
					label: this._('IP-Managed-Client')
				}, {
					id: 'windows',
					label: this._('Windows')
				}]
			}],
			layout: [['school'], ['type']]
		}, {
			name: 'computer',
			headerText: this._('Computer information'),
			helpText: this._('Enter the computer\'s details'),
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
				label: this._('Subnetmask'),
				value: '255.255.255.0'
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
		}];
	},

	postMixInProperties: function() {
		this.finishButtonLabel = this._('Click here to create another computer');
		this.finishTextLabel = this._('The computer has been successfully created.');
	},

	restart: function() {
		umc.tools.forIn(this.getPage('computer')._form._widgets, function(iname, iwidget) {
			iwidget.reset();
		});
		this.inherited(arguments);
	}
});
