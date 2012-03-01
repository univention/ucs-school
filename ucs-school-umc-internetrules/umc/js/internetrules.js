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
/*global console dojo dojox dijit umc */

dojo.provide("umc.modules.internetrules");

dojo.require("umc.tools");
dojo.require("umc.widgets.Module");

dojo.require("umc.modules._internetrules.AssignPage");
dojo.require("umc.modules._internetrules.AdminPage");
dojo.require("umc.modules._internetrules.DetailPage");

dojo.declare("umc.modules.internetrules", umc.widgets.Module, {
	// summary:
	//		Template module to ease the UMC module development.
	// description:
	//		This module is a template module in order to aid the development of
	//		new modules for Univention Management Console.

	// internal reference to the pages
	_assignPage: null,
	_detailPage: null,
	_adminPage: null,

	buildRendering: function() {
		this.inherited(arguments);

		// render the correct pages corresponding to the given flavor
		if (this.moduleFlavor == 'assign') {
			// flavor for assigning rules to groups
			this._assignPage = new umc.modules._internetrules.AssignPage({});
			this.addChild(this._assignPage);
		}
		else {
			// flavor for managing internet rules
			this._adminPage = new umc.modules._internetrules.AdminPage({});
			this.addChild(this._adminPage);
			this._detailPage = new umc.modules._internetrules.DetailPage({});
			this.addChild(this._detailPage);

			// the module needs to handle the visibilities of different pages
			// via the corresponding events
			this.connect(this._adminPage, 'onOpenDetailPage', function(id) {
				this.selectChild(this._detailPage);
				this._detailPage.load(id);
			});
			this.connect(this._detailPage, 'onClose', function(id) {
				this.selectChild(this._adminPage);
			});
		}
	}
});



