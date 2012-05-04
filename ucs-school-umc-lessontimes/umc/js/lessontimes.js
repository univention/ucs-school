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

dojo.provide("umc.modules.lessontimes");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.Form");
dojo.require("umc.widgets.Module");
dojo.require("umc.widgets.Page");

dojo.declare("umc.modules.lessontimes", [ umc.widgets.Module, umc.i18n.Mixin ], {
	postMixInProperties: function() {
		this.inherited(arguments);
		this.standbyOpacity = 1;
	},

	buildRendering: function() {
		this.inherited(arguments);
		this.standby(true);

		this.umcpCommand('lessontimes/get').then(dojo.hitch(this, function(response) {
			this.renderPage(response.result);
			this.standby(false);
		}));
	},

	renderPage: function(values) {
		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		var titlePane = new umc.widgets.ExpandingTitlePane({
			title: this._('Lesson times')
		});

		var widgets = [{
			type: 'MultiInput',
			name: 'lessons',
			label: this._(''),
			subtypes: [{
				type: 'TextBox',
				label: this._('Description')
			}, {
				type: 'TextBox',
				label: this._('Start time'),
				size: 'OneThird'
			}, {
				type: 'TextBox',
				name: 'subject',
				label: this._('End time'),
				size: 'OneThird'
			}],
			value: values
		}];

		var layout = ['lessons'];

		this._form = new umc.widgets.Form({
			region: 'top',
			widgets: widgets,
			layout: layout,
			scrollable: true
		});

		// turn off the standby animation as soon as all form values have been loaded
		this.connect(this._form, 'onValuesInitialized', function() {
			this.standby(false);
		});

		titlePane.addChild(this._form);

		var buttons = [{
            name: 'submit',
            label: this._('Submit'),
            'default': true,
            callback: dojo.hitch(this, function() {
				var values = this._form.gatherFormValues();
	            this.onSubmit(values);
            })
        }, {
            name: 'close',
            label: this._('Close'),
            callback: dojo.hitch(this, function() {
	            umc.dialog.confirm(this._('Should the UMC module be closed? All unsaved modification will be lost.'), [{
		            label: this._('Close'),
		            callback: dojo.hitch(this, function() {
			            dojo.publish('/umc/tabs/close', [this]);
		            })
	            }, {
		            label: this._('Cancel'),
		            'default': true
	            }]);
            })
        }];

		this._page = new umc.widgets.Page({
			headerText: this.description,
			helpText: '',
			footerButtons: buttons
		});

		this.addChild(this._page);
		this._page.addChild(titlePane);
	},

	onSubmit: function(values) {
		this.umcpCommand('lessontimes/set', values).then(dojo.hitch(this, function (response) {
			console.log('onSubmit', values);
		}));
	}
});
