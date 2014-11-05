/*
 * Copyright 2011-2014 Univention GmbH
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
	"umc/store",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/MultiInput",
	"umc/widgets/CheckBox",
	"umc/widgets/ComboBox",
	"umc/widgets/TextBox",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/internetrules"
], function(declare, lang, dialog, store, Page, Form, MultiInput, CheckBox, ComboBox, TextBox, StandbyMixin, _) {

	return declare("umc.modules.internetrules.DetailPage", [ Page, StandbyMixin ], {
		// summary:
		//		This class represents the detail view of our dummy module.

		// reference to the module's store object
		moduleStore: null,

		// internal reference to the formular containing all form widgets of an UDM object
		_form: null,

		postMixInProperties: function() {
			this.inherited(arguments);

			// set the opacity for the standby animation
			this.standbyOpacity = 1;

			// get the module store
			this.moduleStore = store('id', 'internetrules');

			// set the page header
			this.headerText = _('Edit internet rule');

			// configure buttons for the footer of the detail page
			this.footerButtons = [{
				name: 'submit',
				label: _('Save'),
				callback: lang.hitch(this, function() {
					this._save(this._form.get('value'));
				})
			}, {
				name: 'back',
				label: _('Back to overview'),
				callback: lang.hitch(this, 'onClose')
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);
			this.renderDetailPage();
		},

		renderDetailPage: function() {
			// render the form containing all detail information that may be edited

			// specify all widgets
			var widgets = [{
				type: TextBox,
				name: 'name',
				label: _('Name'),
				description: _('The name of the rule')
			}, {
				type: ComboBox,
				name: 'type',
				label: _('Rule type'),
				description: _('A <i>whitelist</i> defines the list of domains that can be browsed to, the access to all other domains will be blocked. A <i>blacklist</i> allows access to all existing domains, only the access to the specified list of domains will be denied.'),
				staticValues: [{
					id: 'whitelist',
					label: _('Whitelist')
				}, {
					id: 'blacklist',
					label: _('Blacklist')
				}]
			}, {
				type: ComboBox,
				name: 'priority',
				label: _('Priority'),
				description: _('The priority allows to define an order in which a set of rules will be applied. A rule with a higher priority will overwrite rules with lower priorities.'),
				value: '5',
				staticValues: [
					{ id: '0', label: _('0 (low)') },
					'1', '2', '3', '4',
					{ id: '5', label: _('5 (average)') },
					'6', '7', '8', '9',
					{ id: '10', label: _('10 (high)') }
				]
			}, {
				type: CheckBox,
				name: 'wlan',
				label: _('WLAN authentification enabled')
			}, {
				type: MultiInput,
				name: 'domains',
				description: _('A list of internet domains, such as wikipedia.org, youtube.com. It is recommended to specify only the last part of a domain, i.e., wikipedia.org instead of www.wikipedia.org.'),
				subtypes: [{
					type: TextBox
				}],
				label: _('Web domains (e.g., wikipedia.org, facebook.com)')
			}];

			// specify the layout... additional dicts are used to group form elements
			// together into title panes
			var layout = [{
				label: _('Rule properties'),
				layout: [ 'name', 'type' ]
			}, {
				label: _('Web domain list'),
				layout: [ 'domains' ]
			}, {
				label: _('Advanced properties'),
				layout: [ 'wlan', 'priority' ]
			}];

			// create the form
			this._form = new Form({
				widgets: widgets,
				layout: layout,
				moduleStore: this.moduleStore,
				// alows the form to be scrollable when the window size is not large enough
				scrollable: true
			});

			// add form to page... the page extends a BorderContainer, by default
			// an element gets added to the center region
			this.addChild(this._form);

			// hook to onSubmit event of the form
			this._form.on('submit', lang.hitch(this, '_save'));
		},

		_save: function(values) {
			this.standby(true);
			this._form.save().then(lang.hitch(this, function(result) {
				this.standby(false);
				if (result && !result.success) {
					// display error message
					dialog.alert(result.details);
					return;
				}
				this.onClose();
				return;
			}), lang.hitch(this, function(error) {
				// server error
				this.standby(false);
			}));
		},

		load: function(id) {
			// during loading show the standby animation
			this.standby(true);
			this._loadedRuleName = id;

			// load the object into the form... the load method returns a
			// Deferred object in order to handel asynchronity
			this._form.load(id).then(lang.hitch(this, function() {
				// done, switch of the standby animation
				this.standby(false);
			}), lang.hitch(this, function() {
				// error handler: switch of the standby animation
				// error messages will be displayed automatically
				this.standby(false);
			}));

			// set focus
			this._form.getWidget('name').focus();
		},

		reset: function() {
			// clear form values and set defaults
			this._form.clearFormValues();
			this._form.setFormValues({
				priority: '5',
				type: 'whitelist'
			});
			this._loadedRuleName = null;

			// set focus
			this._form.getWidget('name').focus();
		},

		onClose: function() {
			// event stub
		}
	});

});
