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
	"dojo/_base/array",
	"dojo/topic",
	"umc/tools",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/PasswordInputBox",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, topic, tools, TextBox, Text, ComboBox, PasswordInputBox, Wizard, _) {

	return declare("umc.modules.schoolwizards.UserWizard", [Wizard], {

		getGeneralPage: function() {
			var page = this.inherited(arguments);
			page.widgets.push({
				type: ComboBox,
				name: 'type',
				label: _('Type'),
				staticValues: [{
					id: 'student',
					label: _('Student')
				}, {
					id: 'teacher',
					label: _('Teacher')
				}, {
					id: 'staff',
					label: _('Staff')
				}, {
					id: 'teachersAndStaff',
					label: _('Teachers and staff')
				}]
			});
			page.layout.push('type');
			return page;
		},

		getItemPage: function() {
			return {
				name: 'item',
				headerText: this.description,
				helpText: this.editMode ? _('Enter details of the user') : _('Enter details to create a new user'),
				buttons: [{
					name: 'newClass',
					label: _('Create a new class'),
					callback: lang.hitch(this, function() {
						topic.publish('/umc/modules/open', 'schoolwizards', 'schoolwizards/classes');
					})
				}],
				widgets: [{
					type: TextBox,
					name: 'firstname',
					label: _('Firstname'),
					required: true
				}, {
					type: TextBox,
					name: 'lastname',
					label: _('Lastname'),
					required: true
				}, {
					type: TextBox,
					name: 'name',
					label: _('Username'),
					disabled: this.editMode,
					required: true
				}, {
					type: ComboBox,
					name: 'school_class',
					label: _('Class')
				}, {
					type: TextBox,
					name: 'email',
					label: _('E-Mail')
				}, {
					type: PasswordInputBox,
					name: 'password',
					label: _('Password'),
					focus: lang.hitch(this, function() {
						// just a workaround for Bug #30110
						var widget = this.getWidget('item', 'password');
						if (! widget._firstWidget.get('value')) {
							widget._firstWidget.focus();
						} else {
							widget._secondWidget.focus();
						}
					}),
					validate: lang.hitch(this, function() {
						// ...and another one for Bug #30109
						return this.getWidget('item', 'password').isValid();
					})
				}],
				layout: [
					['firstname', 'lastname'],
					['name'],
					['school_class', 'newClass'],
					['email'],
					['password']
				]
			};
		},

		restart: function() {
			tools.forIn(this.getPage('item')._form._widgets, function(iname, iwidget) {
				if (iname === 'password') {
					iwidget._setValueAttr(null);
				} else if (iname !== 'school_class') {
					iwidget.reset();
				}
			});
			this.inherited(arguments);
		},

		addNote: function() {
			var name = this.getWidget('item', 'name').get('value');
			var message = _('User "%s" has been successfully created. Continue to create another user or press "Cancel" to close this wizard.', name);
			this.getPage('item').clearNotes();
			this.getPage('item').addNote(message);
		},

		updateWidgets: function(/*String*/ currentPage) {
			if (currentPage === 'general') {
				var selectedType = this.getWidget('general', 'type').get('value');
				var types = ['teacher', 'staff', 'teachersAndStaff'];
				var classBox = this.getWidget('item', 'school_class');
				var newClassButton = this.getPage('item')._form.getButton('newClass');
				if (array.indexOf(types, selectedType) >= 0) {
					classBox.set('value', null);
					classBox.set('required', false);
					classBox.hide();
					newClassButton.hide();
				} else {
					classBox.set('required', true);
					classBox.show();
					newClassButton.show();
					this.reloadClasses();
				}
			}
		},

		onShow: function() {
			this.reloadClasses();
		},

		reloadClasses: function() {
			var schoolName = this.getWidget('general', 'school').get('value');
			if (schoolName) {
				this.umcpCommand('schoolwizards/classes', {'school': schoolName}).then(
					lang.hitch(this, function(response) {
						var classes = array.map(response.result, function(item) {
							return item.label;
						});
						var widget = this.getWidget('item', 'school_class');
						widget.set('staticValues', classes);
						if (this.loadedValues && this.loadedValues.school_class) {
							widget.set('value', this.loadedValues.school_class);
						}
					})
				);
			}
		}
	});
});

