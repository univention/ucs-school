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
	"umc/widgets/Module",
	"umc/modules/internetrules/AssignPage",
	"umc/modules/internetrules/AdminPage",
	"umc/modules/internetrules/DetailPage",
	"umc/i18n!umc/modules/internetrules"
], function(declare, lang, Module, AssignPage, AdminPage, DetailPage, _) {

	return declare("umc.modules.internetrules", [ Module ], {
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
				this._assignPage = new AssignPage({});
				this.addChild(this._assignPage);
			}
			else {
				// flavor for managing internet rules
				this._adminPage = new AdminPage({});
				this.addChild(this._adminPage);
				this._detailPage = new DetailPage({});
				this.addChild(this._detailPage);

				// the module needs to handle the visibilities of different pages
				// via the corresponding events
				this._adminPage.on('OpenDetailPage', lang.hitch(this, function(id) {
					this.selectChild(this._detailPage);
					if (undefined === id) {
						// a new rule is being added
						this._detailPage.reset(id);
					}
					else {
						// an existing rule is being opened
						this._detailPage.load(id);
					}
				}));
				this._detailPage.on('close', lang.hitch(this, function(id) {
					this.selectChild(this._adminPage);
				}));

				// if the flavor is not 'admin', we open the admin page with the given flavor as id
				if (this.moduleFlavor != 'admin') {
					this._adminPage.onOpenDetailPage(this.moduleFlavor);
				}
			}
		}
	});

});
