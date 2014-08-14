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
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, TextBox, ComboBox, Wizard, _) {

	return declare("umc.modules.schoolwizards.SchoolWizard", [Wizard], {
		getGeneralPage: function() {
			// no need for "school" and "type" widgets
			return null;
		},

		addUDMLink: function() {
			// no link to UDM module
		},

		getItemPage: function() {
			var widgets = [{
					type: TextBox,
					name: 'display_name',
					label: _('Name of the school'),
					description: _("The given value will be shown as school's name within UCS@school."),
					required: true
				}, {
					type: TextBox,
					name: 'name',
					label: _('School abbreviation'),
					description: _('The given value will be used as object name for the new school OU object within the LDAP directory and as prefix for several school objects like group names. It may consist of the letters a-z, the digits 0-9 and underscores. Usually it is safe to keep the suggested value.'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$',
					depends: ['display_name'],
					dynamicValue: lang.hitch(this, function(values) {
						if (this.editMode) {
							return values.name;
						}
						return values.display_name.replace(/[^a-zA-Z0-9]/g, '');
					}),
					disabled: this.editMode,
					required: true
				}, {
					type: TextBox,
					name: 'dc_name',
					label: _('Name of educational school server'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9-]*)([a-zA-Z0-9]$))?$',
					description: _('Name of the educational domaincontroller slave for the new school. The server name may consist of the letters a-z, the digits 0-9 and hyphens (-). The name of the educational server may not be equal to the administrative server!'),
					maxLength: 12,
					required: !this.editMode && !this.singleMaster,
					visible: !this.editMode && !this.singleMaster
				}];
			if (this.editMode) {
				widgets.push({
					name: 'home_share_file_server',
					type: ComboBox,
					label: _('Server for Windows home directories'),
					dynamicValues: lang.hitch(this, function() {
						return this.umcpCommand('schoolwizards/schools/share_servers').then(function(data) {
							return data.result;
						});
					})
				});
				widgets.push({
					name: 'class_share_file_server',
					type: ComboBox,
					label: _('Server for class shares'),
					dynamicValues: lang.hitch(this, function() {
						return this.umcpCommand('schoolwizards/schools/share_servers').then(function(data) {
							return data.result;
						});
					})
				});
			}
			return {
				name: 'item',
				headerText: this.description,
				widgets: widgets,
				layout: this.getSchoolPageLayout()
			};
		},

		getSchoolPageLayout: function() {
			var layout = [
				['display_name'],
				['name'],
				['dc_name']
			];
			if (this.editMode) {
				return [{
					label: _('School information'),
					layout: layout
				}, {
					label: _('Advanced settings'),
					open: false,
					layout: ['home_share_file_server', 'class_share_file_server']
				}];
			}
			return layout;
		},

		restart: function() {
			this.getWidget('item', 'display_name').reset();
			this.getWidget('item', 'name').reset();
			this.getWidget('item', 'dc_name').reset();
			this.inherited(arguments);
		},

		addNote: function() {
			var display_name = this.getWidget('item', 'display_name').get('value');
			var message = _('The school "%s" has been successfully created. Continue to create another school or press "Cancel" to close this wizard.', display_name);
			this.getPage('item').clearNotes();
			this.getPage('item').addNote(message);
		}
	});
});

