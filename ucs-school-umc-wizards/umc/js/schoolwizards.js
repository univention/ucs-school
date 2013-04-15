/*
 * Copyright 2012-2013 Univention GmbH
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
	"dojo/topic",
	"umc/widgets/Module",
	"umc/modules/schoolwizards/UserWizard",
	"umc/modules/schoolwizards/ClassWizard",
	"umc/modules/schoolwizards/ComputerWizard",
	"umc/modules/schoolwizards/SchoolWizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, topic, Module, UserWizard, ClassWizard, ComputerWizard, SchoolWizard, _) {

	return declare("umc.modules.schoolwizards", [ Module ], {

		// internal reference to our wizard
		_wizard: null,

		buildRendering: function() {
			this.inherited(arguments);
			this._wizard = this._getWizard(this.moduleFlavor);
			if (this._wizard) {
				this.addChild(this._wizard);

				this._wizard.on('finished', lang.hitch(this, function() {
					topic.publish('/umc/tabs/close', this);
				}));
				this._wizard.on('cancel', lang.hitch(this, function() {
					topic.publish('/umc/tabs/close', this);
				}));
			}

			if ('onShow' in this._wizard) {
				// send a reload command to wizard
				this.on('show', lang.hitch(this, function(evt) {
					this._wizard.onShow();
				}));
			}
		},

		_getWizard: function(moduleFlavor) {
			var Wizard = null;
			switch (moduleFlavor) {
				case 'schoolwizards/users':
					Wizard = UserWizard;
					break;
				case 'schoolwizards/classes':
					Wizard = ClassWizard;
					break;
				case 'schoolwizards/computers':
					Wizard = ComputerWizard;
					break;
				case 'schoolwizards/schools':
					Wizard = SchoolWizard;
					break;
				default: return null;
			}
			return new Wizard({
				description: this.description,
				umcpCommand: lang.hitch(this, 'umcpCommand')
			});
		}
	});

});
