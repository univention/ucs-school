/*
 * Copyright 2011-2015 Univention GmbH
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
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/StandbyMixin",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiObjectSelect",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, array, Page, Form, StandbyMixin, TextBox, ComboBox, MultiObjectSelect, _) {

	return declare("umc.modules.schoolgroups.DetailPage", [ Page, StandbyMixin ], {
		moduleStore: null,
		moduleFlavor: null,
		umcpCommand: null,
		_form: null,
		standbyOpacity: 1,

		multiWidgetName: 'members',

		postMixInProperties: function() {
			this.inherited(arguments);

			// configure buttons for the footer of the detail page
			this.footerButtons = [{
				name: 'submit',
				label: _('Save changes'),
				callback: lang.hitch(this, '_save')
			}, {
				name: 'back',
				label: _('Back to overview'),
				callback: lang.hitch(this, 'onClose')
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._form = new Form({
				widgets: this.getWidgets(),
				moduleStore: this.moduleStore
			});
			this.addChild(this._form);

			this._form.getWidget(this.multiWidgetName).on('ShowDialog', lang.hitch(this, function(_dialog) {
				_dialog._form.getWidget('school').setInitialValue(this._form.getWidget('school').get('value'), true);
			}));

			this._form.on('submit', lang.hitch(this, '_save'));
		},

		getWidgets: function() {
			return [];
		},

		getMultiSelectWidget: function() {
			return {
				type: MultiObjectSelect,
				name: this.multiWidgetName,
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
			};
		},

		getMultiSelectGroup: function() {
			return {
				type: ComboBox,
				name: 'group',
				label: _('User group or class'),
				depends: 'school',
				dynamicValues: 'schoolgroups/classes',
				umcpCommand: lang.hitch(this, 'umcpCommand')
			};
		},

		_save: function() {
			var values = this._form.get('value');
			var deferred = null;
			var nameWidget = this._form.getWidget('name');

			if (!this._form.validate()) {
				nameWidget.focus();
				return;
			}

			if (values.$dn$) {
				deferred = this.moduleStore.put(values);
			} else {
				deferred = this.moduleStore.add(values);
			}

			deferred.then(lang.hitch(this, function() {
				this.onClose();
			}));
		},

		disableFields: function(disable) {
			this._form.getWidget('school').set('disabled', disable);
			this._form.getWidget('name').set('disabled', disable);
		},

		_setSchoolAttr: function(school) {
			this._form.getWidget('school').set('value', school);
		},

		_setSchoolsAttr: function(schools) {
			var school = this._form.getWidget('school');
			school.set('staticValues', schools);
			school.set('visible', schools.length > 1);
		},

		load: function(id) {
			// this._form.getWidget('name').setValid(null);
			this.standbyDuring(this._form.load(id));
		},

		onClose: function(dn, objectType) {
			// event stub
		}
	});

});
