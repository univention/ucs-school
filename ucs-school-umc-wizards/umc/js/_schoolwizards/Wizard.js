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

dojo.provide("umc.modules._schoolwizards.Wizard");

dojo.require("umc.i18n");
dojo.require("umc.widgets.Wizard");

dojo.declare("umc.modules._schoolwizards.Wizard", [ umc.widgets.Wizard, umc.i18n.Mixin ], {

	// use i18n information from umc.modules.schoolwizards
	i18nClass: 'umc.modules.schoolwizards',

	createObjectCommand: null,

	finishHelpText: null,
	finishButtonLabel: null,
	finishTextLabel: null,

	buildRendering: function() {
		this.pages.push({
			name: 'finish',
			headerText: this._('Finished'),
			helpText: this.finishHelpText,
			widgets: [{
				name: 'resultMessage',
				type: 'Text',
				content: '<p>' + this.finishTextLabel + '</p>'
			}],
			buttons: [{
				name: 'createAnother',
				label: this.finishButtonLabel,
				onClick: dojo.hitch(this, 'restart')
			}],
			layout: [['resultMessage'],
			         ['createAnother']]
		});
		this.inherited(arguments);
	},

	hasPrevious: function(/*String*/ pageName) {
		return pageName === 'finish' ? false : this.inherited(arguments);
	},

	canCancel: function(/*String*/ pageName) {
		return pageName === 'finish' ? false : true;
	},

	next: function(/*String*/ currentPage) {
		var nextPage = this.inherited(arguments);
		if (this._getPageIndex(currentPage) === (this.pages.length -2 )) {
			if (this._validateForm()) {
				return this._createObject().then(dojo.hitch(this, function(result) {
					return result ? nextPage : currentPage;
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
		return umc.tools.umcpCommand(this.createObjectCommand , values).then(
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
	},

	restart: function() {
		// Select the first page
		var firstPageName = this.pages[0].name;
		this._updateButtons(firstPageName);
		this.selectChild(this._pages[firstPageName]);
	}
});
