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

dojo.provide("umc.modules.schoolwizards");

dojo.require("umc.i18n");
dojo.require("umc.widgets.Module");

dojo.require("umc.modules._schoolwizards.UserWizard");
dojo.require("umc.modules._schoolwizards.ClassWizard");
dojo.require("umc.modules._schoolwizards.ComputerWizard");
dojo.require("umc.modules._schoolwizards.SchoolWizard");

dojo.declare("umc.modules.schoolwizards", [ umc.widgets.Module, umc.i18n.Mixin ], {

	// internal reference to our wizard
	_wizard: null,

	buildRendering: function() {
		this.inherited(arguments);
		this._wizard = this._getWizard(this.moduleFlavor);
		if (this._wizard) {
			this.addChild(this._wizard);

			this.connect(this._wizard, 'onFinished', function() {
				dojo.publish('/umc/tabs/close', [this]);
			});
			this.connect(this._wizard, 'onCancel', function() {
				dojo.publish('/umc/tabs/close', [this]);
			});
		}

		if ('onShow' in this._wizard) {
			// send a reload command to wizard
			this.connect(this, 'onShow', function(evt) {
				this._wizard.onShow();
			});
		}
	},

	_getWizard: function(moduleFlavor) {
		var path = umc.modules._schoolwizards;
		var Wizard = null;
		switch (moduleFlavor) {
			case 'schoolwizards/users':
				Wizard = path.UserWizard;
				break;
			case 'schoolwizards/classes':
				Wizard = path.ClassWizard;
				break;
			case 'schoolwizards/computers':
				Wizard = path.ComputerWizard;
				break;
			case 'schoolwizards/schools':
				Wizard = path.SchoolWizard;
				break;
			default: return null;
		}
		return new Wizard({
			description: this.description
		});
	}
});
