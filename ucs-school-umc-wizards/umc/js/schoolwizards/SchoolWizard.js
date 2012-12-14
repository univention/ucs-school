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
	"dojo/_base/lang",
	"umc/tools",
	"umc/widgets/TextBox",
	"umc/modules/schoolwizards/Wizard",
	"umc/i18n!/umc/modules/schoolwizards"
], function(declare, lang, tools, TextBox, Wizard, _) {

	return declare("umc.modules.schoolwizards.SchoolWizard", [ Wizard ], {

		createObjectCommand: 'schoolwizards/schools/create',

		postMixInProperties: function() {
			this.inherited(arguments);
			this.pages = [{
				name: 'school',
				headerText: this.description,
				helpText: _('Enter details to create all necessary structures for a new school.'),
				widgets: [{
					type: TextBox,
					name: 'name',
					label: _('Name of the school'),
					regExp: '^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$',
					required: true
				}, {
					type: TextBox,
					name: 'schooldc',
					label: _('Computer name of the school server'),
					regExp: '^\\w+$',
					required: true
				}],
				layout: [['name'],
			         	 ['schooldc']]
			}];
		},

		postMixInProperties: function() {
			this.inherited(arguments);
			this.standbyOpacity = 1;
		},

		buildRendering: function() {
			this.inherited(arguments);
			this.standby(true);

			tools.umcpCommand('schoolwizards/schools/singlemaster').then(lang.hitch(this, function(response) {
				if (response.result.isSinglemaster) {
					var widget = this.getWidget('school', 'schooldc');
					widget.hide();
					widget.set('required', false);
				}
				this.standby(false);
			}), lang.hitch(this, function() {
				this.standby(false);
			}));
		},

		restart: function() {
			this.getWidget('school', 'name').reset();
			this.getWidget('school', 'schooldc').reset();
			this.inherited(arguments);
		},

		addNote: function() {
			var name = this.getWidget('school', 'name').get('value');
			var message = _('School "%s" has been successfully created. Continue to create another school or press "Cancel" to close this wizard.', name);
			this.getPage('school').clearNotes();
			this.getPage('school').addNote(message);
		}
	});

});
