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

dojo.declare("umc.modules._schoolwizards.SchoolWizard", [ umc.modules._schoolwizards.Wizard, umc.i18n.Mixin ], {

	constructor: function() {
		this.pages = [{
			name: 'school',
			headerText: this._('General information'),
			helpText: this._('Here\'s a simple helpText'),
			widgets: [{
				type: 'TextBox',
				name: 'name',
				label: this._('Name'),
				required: true
			}],
			layout: [['name']]
		}, {
			name: 'finish',
			headerText: this._('Finished'),
			helpText: this._('Here\'s a simple helpText')
		}];
	},

	next: function(/*String*/ currentPage) {
		var nextPage = this.inherited(arguments);
		if (currentPage === 'school') {
			if (this._validateForm()) {
				return this._createSchool().then(dojo.hitch(this, function(result) {
					return result ? nextPage : currentPage;
				}));
			} else {
				return currentPage;
			}
		}
		return nextPage;
	},

	_createSchool: function() {
		this.standby(true);
		var values = this.getValues();
		return umc.tools.umcpCommand('schoolwizards/schools/create', values).then(
			dojo.hitch(this, function(response) {
				this.standby(false);
				if (response.result) {
					umc.dialog.alert(response.result.message);
					return false;
				} else {
					return true;
				}
			}),
			dojo.hitch(this, function(result) {
				this.standby(false);
				return false;
			})
		);
	}
});
