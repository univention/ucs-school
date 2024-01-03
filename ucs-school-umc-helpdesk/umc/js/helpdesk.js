/*
 * Copyright 2012-2024 Univention GmbH
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
	"umc/dialog",
	"umc/widgets/ComboBox",
	"umc/widgets/Form",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/TextArea",
	"umc/i18n!umc/modules/helpdesk"
], function(declare, lang, dialog, ComboBox, Form, Module, Page, TextArea, _) {
	return declare("umc.modules.helpdesk", [ Module ], {

		buildRendering: function() {
			this.inherited(arguments);

			this._page = new Page({
				mainContentClass: 'umcCard2'
			});

			var widgets = [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				autoHide: true,
				dynamicValues: 'helpdesk/schools'
			}, {
				type: ComboBox,
				name: 'category',
				label: _('Category'),
				dynamicValues: 'helpdesk/categories'
			}, {
				type: TextArea,
				name: 'message',
				// FIXME: rows don't work.
				rows: 10,
				size: 'Two',
				label: _('Message to the helpdesk team')
			}];

			var layout = [
				['school', 'category'],
				'message'
			];

			var buttons = [{
				name: 'submit',
				label: _('Send'),
				callback: lang.hitch(this, function() {
					var values = this._form.get('value');
					if (values.message) {
						this.onSubmit(this._form.get('value'));
					} else {
						dialog.alert(_('The required message is missing. Therefore, no report has been sent to the helpdesk team.'));
					}
				})
			}];

			this._form = new Form({
				widgets: widgets,
				layout: layout,
				buttons: buttons
			});
			this.standbyDuring(this._form.ready());


			this.addChild(this._page);
			this._page.addChild(this._form);
		},

		onSubmit: function(values) {
			this.standbyDuring(this.umcpCommand('helpdesk/send', values)).then(lang.hitch(this, function(response) {
				dialog.alert(_('The report has been sent to the helpdesk team'));
				this._form._widgets.message.set('value', '');
			}));
		}
	});
});
