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
	"dojo/_base/array",
	"dojo/_base/lang",
	"dojo/on",
	"dojo/topic",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/ComboBox",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Form",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/TextArea",
	"umc/widgets/TextBox",
	"umc/i18n!umc/modules/helpdesk"
], function(declare, array, lang, on, topic, dialog, tools, ComboBox,
            ExpandingTitlePane, Form, Grid, Module, Page, SearchForm, TextArea,
            TextBox, _) {
	return declare("umc.modules.helpdesk", [ Module ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

		postMixInProperties: function() {
			// is called after all inherited properties/methods have been mixed
			// into the object (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			// Set the opacity for the standby animation to 100% in order to mask
			// GUI changes when the module is opened. Call this.standby(true|false)
			// to enabled/disable the animation.
			this.standbyOpacity = 1;
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			// it is important to call the parent's buildRendering() method
			this.inherited(arguments);

			// start the standby animation in order prevent any interaction before the
			// form values are loaded
			this.standby(true);

			// render the page containing search form and grid
			this.umcpCommand('helpdesk/configuration').then(
				lang.hitch(this, function(response) {
					if (response.result.recipient) {
						this.renderPage(response.result.username, response.result.school);
						this.standby(false);
					} else {
						dialog.alert(_('The helpdesk module is not configured properly. The recipient email address is not set.'));
						on.once(dialog._alertDialog, 'confirm', lang.hitch(this, function() {
							topic.publish('/umc/tabs/close', this);
						}));
					}
				})
			);
		},

		renderPage: function(username, school) {
			// ExpandingTitlePane is an extension of dijit.layout.BorderContainer
			var titlePane = new ExpandingTitlePane({
				title: _('Message to the helpdesk team')
			} );

			//
			// form
			//

			// add remaining elements of the search form
			var widgets = [{
				type: TextBox,
				name: 'username',
				label: _('User name'),
				value: username,
				disabled: true
			}, {
				type: TextBox,
				name: 'school',
				label: _('School'),
				value: school,
				disabled: true
			}, {
				type: ComboBox,
				name: 'category',
				label: _('Category'),
				dynamicValues: 'helpdesk/categories'
			}, {
				type: TextArea,
				name: 'message',
				style: 'height: 200px;',
				label: _('Message')
			} ];

			// the layout is an 2D array that defines the organization of the form elements...
			// here we arrange the form elements in one row and add the 'submit' button
			var layout = [
				'username',
				'school',
				'category',
				'message'
			];

			// generate the form
			this._form = new Form({
				// property that defines the widget's position in a dijit.layout.BorderContainer
				region: 'top',
				widgets: widgets,
				layout: layout
			});

			// turn off the standby animation as soon as all form values have been loaded
			this._form.on('valuesInitialized', lang.hitch(this, function() {
				this.standby(false);
			}));

			// add form to the title pane
			titlePane.addChild(this._form);

			// submit changes
			var buttons = [{
				name: 'submit',
				label: _('Send'),
				'default': true,
				callback: lang.hitch(this, function() {
					var values = this._form.get('value');
					if (values.message) {
						this.onSubmit(this._form.get('value'));
					} else {
						dialog.alert(_('The required message is missing. Therefore, no report has been sent to the helpdesk team.'));
					}
				})
			}, {
				name: 'close',
				label: _('Close'),
				callback: lang.hitch(this, function() {
					var values = this._form.get('value');
					if (values.message) {
						dialog.confirm(_('Should the UMC module be closed? All unsaved modification will be lost.'), [{
							label: _('Close'),
							callback: lang.hitch(this, function() {
								topic.publish('/umc/tabs/close', this);
							})
						}, {
							label: _('Cancel'),
							'default': true
						}]);
					} else {
						topic.publish('/umc/tabs/close', this);
					}
				})
			}];

			this._page = new Page({
				headerText: this.description,
				helpText: '',
				footerButtons: buttons
			});

			this.addChild(this._page);
			this._page.addChild(titlePane);
		},

		onSubmit: function(values) {
			this.umcpCommand('helpdesk/send', values).then(
				lang.hitch(this, function(response) {
					if (response.result) {
						dialog.alert(_('The report has been sent to the helpdesk team'));
						this._form._widgets.message.set('value', '');
					} else {
						dialog.alert(_('The message could not be send to the helpdesk team: ') + response.message);
					}
				})
			);
		}
	});
});
