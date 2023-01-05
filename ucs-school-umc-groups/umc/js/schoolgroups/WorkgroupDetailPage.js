/*
 * Copyright 2015-2023 Univention GmbH
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
	"dojo/_base/array",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/CheckBox",
	"umc/modules/schoolgroups/DetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, array, MultiObjectSelect, TextBox, ComboBox, CheckBox, DetailPage, _) {

	return declare("umc.modules.schoolgroups.WorkgroupDetailPage", [DetailPage], {
		mailAddressPattern: '',

		getWidgets: function() {
			return [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				staticValues: [],
				onChange: lang.hitch(this, function() {
					if (this._form.getWidget('create_email').value && !this._form.getWidget('email_exists').value) {
						this._form.getWidget('email').set('value', this.calculateEmail());
					}
					this._form.getWidget(this.multiWidgetName).set('value', []);
				}),
			},
				{
				type: TextBox,
				name: 'name',
				label: _('Workgroup'),
				disabled: this.moduleFlavor != 'workgroup-admin',
				regExp: '^[a-zA-Z0-9]([a-zA-Z0-9 _.-]*[a-zA-Z0-9])?$',
				invalidMessage: _('May only consist of letters, digits, spaces, dots, hyphens, underscore. Has to start and to end with a letter or a digit.'),
				onChange: lang.hitch(this, function() {
					if (this._form.getWidget('create_email').value && !this._form.getWidget('email_exists').value) {
						this._form.getWidget('email').set('value', this.calculateEmail());
					}
				}),
				required: true
			}, {
				type: TextBox,
				name: 'description',
				label: _('Description'),
				description: _('Verbose description of the group'),
				disabled: this.moduleFlavor != 'workgroup-admin'
			}, this.getMultiSelectWidget(),
				{
				type: CheckBox,
				name: 'create_share',
				label: _('Create share'),
				description: _('If checked, a share is created for the new group'),
				disabled: this.moduleFlavor != 'workgroup-admin',
				value: true
				},
				{ // This widget only exists to hold the information if an email was delivered by the backend in editMode
				type: CheckBox,
				name: 'email_exists',
				visible: false,
				value: false
				},
				{
				type: CheckBox,
				name: 'create_email',
				label: _('Activate Email Address'),
				description: _('If checked an email address will be created for this group'),
				visible: Boolean(this.mailAddressPattern),
				disabled: false,
				value: false,
				onChange: lang.hitch(this, function(newValue) {
					if (newValue && !this._form.getWidget('email_exists').value) {
						this._form.getWidget('email').set('value', this.calculateEmail());
					}
					this._form.getWidget('email').set('visible', newValue);
					this._form.getWidget('allowed_email_senders_users').set('visible', newValue);
					this._form.getWidget('allowed_email_senders_groups').set('visible', newValue);
				})
				},
				{
				type: TextBox,
				name: 'email',
				label: _('Email address'),
				visible: false,
				disabled: true,
				},
				{
				type: MultiObjectSelect,
				name: 'allowed_email_senders_users',
				label: _('Restrict permission to send emails to this group to the following users'),
				visible: false,
				queryWidgets: array.filter([{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					dynamicValues: 'schoolgroups/schools',
					umcpCommand: lang.hitch(this, 'umcpCommand'),
					autoHide: true
				}, this.getMultiSelectGroup(), {
					type: TextBox,
					name: 'pattern',
					label: _('Name')
				}], function(i) { return i; }),
				queryCommand: lang.hitch(this, function(options) {
					return this.umcpCommand('schoolgroups/users', options).then(function(data) {
						return data.result;
					});
				}),
				queryOptions: function() { return {}; },
				autoSearch: false
				},
				{
				type: MultiObjectSelect,
				name: 'allowed_email_senders_groups',
				label: _('Restrict permission to send emails to this group to the following groups'),
				visible: false,
				queryWidgets: array.filter([{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					dynamicValues: 'schoolgroups/schools',
					umcpCommand: lang.hitch(this, 'umcpCommand'),
					autoHide: true
				}, {
					type: TextBox,
					name: 'pattern',
					label: _('Name')
				}], function(i) { return i; }),
				queryCommand: lang.hitch(this, function(options) {
					return this.umcpCommand('schoolgroups/groups', options).then(function(data) {
						return data.result;
					});
				}),
				queryOptions: function() { return {}; },
				autoSearch: false
			}
			];
		},

		setupEditMode: function() {
			this.inherited(arguments)
			var shareWidget = this._form.getWidget('create_share');
			shareWidget.set('disabled', true);
			shareWidget.set('label', _('Share created'));
		},

		calculateEmail: function() {
			var emailString = this.mailAddressPattern;
			var replacementDict = {
				'{ou}': this._form.getWidget('school').value || '{ou}',
				'{name}': this._form.getWidget('name').value || '{name}'
			};
			for (const entry in replacementDict) {
				emailString = emailString.replace(new RegExp(entry, "g"), replacementDict[entry]);
			}
			return emailString
		},

		getMultiSelectWidget: function() {
			return lang.mixin(this.inherited(arguments), {
				label: this.moduleFlavor == 'workgroup' ? _('Students') : _('Members'),
				description: _('Teachers and students that belong to the current workgroup'),
				queryOptions: lang.hitch(this, function() {
					if (this.moduleFlavor == 'workgroup') {
						return { group: 'student' };
					}
					return {};
				})
			});
		},
		getMultiSelectGroup: function() {
			var groups = [];
			if (this.moduleFlavor == 'workgroup-admin') {
				groups.push({id: 'None', label: _('All users')});
				groups.push({id: 'teacher', label: _('All teachers')});
			}
			groups.push({id: 'student', label: _('All students')});
			return lang.mixin(this.inherited(arguments), {
				staticValues: groups
			});
		}

	});
});
