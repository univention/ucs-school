/*
 * Copyright 2012-2014 Univention GmbH
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
	"umc/dialog",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Form",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/MultiInput",
	"umc/widgets/TextBox",
	"umc/widgets/TimeBox",
	"umc/i18n!umc/modules/lessontimes"
], function(declare, lang, topic, dialog, ContainerWidget, Form, Module, Page, MultiInput, TextBox, TimeBox, _) {

	return declare("umc.modules.lessontimes", [ Module ], {

		standbyOpacity: 1,

		buildRendering: function() {
			this.inherited(arguments);

			this.standbyDuring(this.umcpCommand('lessontimes/get')).then(lang.hitch(this, function(response) {
				this.renderPage(response.result);
			}));
		},

		renderPage: function(values) {
			var widgets = [{
				type: MultiInput,
				name: 'lessons',
				label: _(''),
				subtypes: [{
					type: TextBox,
					name: 'description',
					label: _('Description'),
					size: 'TwoThirds'
				}, {
					type: TimeBox,
					name: 'begin',
					label: _('Start time'),
					size: 'TwoThirds'
				}, {
					type: TimeBox,
					name: 'end',
					label: _('End time'),
					size: 'TwoThirds'
				}],
				value: values
			}];

			var layout = [{
				label: _('Lesson times'),
				layout: ['lessons']
			}];

			this._form = new Form({
				region: 'top',
				widgets: widgets,
				layout: layout
			});

			// turn off the standby animation as soon as all form values have been loaded
			this._form.on('ValuesInitialized', lang.hitch(this, function() {
				this.standby(false);
			}));

			var buttons = [{
				name: 'submit',
				label: _('Submit'),
				'default': true,
				callback: lang.hitch(this, function() {
					var values = this._form.get('value');
					this.onSubmit(values);
				})
			}, {
				name: 'close',
				label: _('Close'),
				callback: lang.hitch(this, function() {
					dialog.confirm(_('Should the UMC module be closed? All unsaved modification will be lost.'), [{
						label: _('Close'),
						callback: lang.hitch(this, function() {
							topic.publish('/umc/tabs/close', this);
						})
					}, {
						label: _('Cancel'),
						'default': true
					}]);
				})
			}];

			this._page = new Page({
				headerText: this.description,
				helpText: _('The lesson times are used internally for the default session duration by the computer room module. It is advisable to set the end time of a lesson to a time immediately before the beginning of the following lesson.'),
				footerButtons: buttons
			});
			this.addChild(this._page);

			var container = new ContainerWidget({
				scrollable: true
			});
			this._page.addChild(container);

			container.addChild(this._form);
		},

		onSubmit: function(values) {
			this.standbyDuring(this.umcpCommand('lessontimes/set', values)).then(lang.hitch(this, function(response) {
				if (response.result.message) {
					dialog.alert(response.result.message);
				}
			}));
		}
	});
});
