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

/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Wizard",
	"umc/i18n!/umc/modules/schoolwizards"
], function(declare, lang, tools, dialog, Wizard, _) {

	return declare("umc.modules.schoolwizards.Wizard", [ Wizard ], {

		createObjectCommand: null,

		// set via the module
		description: null,

		hasNext: function() {
			return true;
		},

		next: function(/*String*/ currentPage) {
			var nextPage = this.inherited(arguments);
			this.updateWidgets(currentPage);
			if (this._getPageIndex(currentPage) === (this.pages.length - 1 )) {
				if (this._validateForm()) {
					return this._createObject().then(lang.hitch(this, function(result) {
						if (result) {
							this.addNote();
							this.restart();
						}
						return currentPage;
					}));
				} else {
					return currentPage;
				}
			}
			return nextPage;
		},

		_validateForm: function() {
			var form = this.selectedChildWidget.get('_form');
			if (! form.validate()) {
				var widgets = form.getInvalidWidgets();
				form.getWidget(widgets[0]).focus();
				return false;
			} else {
				return true;
			}
		},

		_createObject: function() {
			this.standby(true);
			var values = this.getValues();
			return tools.umcpCommand(this.createObjectCommand , values).then(
				lang.hitch(this, function(response) {
					this.standby(false);
					if (response.result) {
						dialog.alert(response.result.message);
						return false;
					} else {
						return true;
					}
				}),
				lang.hitch(this, function(result) {
					this.standby(false);
					return false;
				})
			);
		},

		restart: function() {
			// Select the first page
			var firstPageName = this.pages[0].name;
			this._updateButtons(firstPageName);
			this.selectChild(this._pages[firstPageName]);
		},

		updateWidgets: function(/*String*/ currentPage) {
		}
	});

});
