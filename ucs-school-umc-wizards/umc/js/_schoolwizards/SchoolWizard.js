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

dojo.provide("umc.modules._schoolwizards.SchoolWizard");

dojo.require("umc.dialog");
dojo.require("umc.i18n");

dojo.require("umc.modules._schoolwizards.Wizard");

dojo.declare("umc.modules._schoolwizards.SchoolWizard", [ umc.modules._schoolwizards.Wizard, umc.i18n.Mixin ], {

	createObjectCommand: 'schoolwizards/schools/create',

	constructor: function() {
		this.pages = [{
			name: 'school',
			headerText: this.description,
			helpText: this._('Enter details to create all necessary structures for a new school.'),
			widgets: [{
				type: 'TextBox',
				name: 'name',
				label: this._('Name'),
				required: true
			}, {
				type: 'TextBox',
				name: 'schooldc',
				label: this._('School DC'),
			}],
			layout: [['name'],
			         ['schooldc']]
		}];
	},

	restart: function() {
		this.getWidget('school', 'name').reset();
		this.inherited(arguments);
	},

	addNote: function() {
		var name = this.getWidget('school', 'name').get('value');
		var message = this._('School "%s" has been successfully created. Continue to create another school or press "Cancel" to close this wizard.', name);
		this.getPage('school').clearNotes();
		this.getPage('school').addNote(message);
	}
});
