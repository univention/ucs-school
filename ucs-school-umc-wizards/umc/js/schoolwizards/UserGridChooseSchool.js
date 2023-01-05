/*
 * Copyright 2012-2023 Univention GmbH
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
	"dojox/html/entities",
	"umc/widgets/Form",
	"umc/widgets/Page",
	"umc/widgets/ComboBox",
	"umc/widgets/Text",
	"umc/modules/schoolwizards/UserGrid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, entities, Form, Page, ComboBox, Text, UserGrid, _) {

	return declare("umc.modules.schoolwizards.UserGridChooseSchool", [Page], {
		userGrid: null,
		baseTitle: null,
		_form: null,

		mainContentClass: 'umcCard2',

		postMixInProperties: function() {
			this.baseTitle = this.module.get('title');
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._form = this.createForm();
			this._form.on('submit', lang.hitch(this, 'buildGrid'));

			this.addChild(this._form);
			if (this.schools.length <= 1) {
				this._form.ready().then(lang.hitch(this, 'buildGrid'));
			}
		},

		createForm: function() {
			return new Form({
				widgets: [{
					type: Text,
					size: 'One',
					name: 'headerText',
					content: '<h2>' + entities.encode(_('Please select a school')) + '<h2>'
				}, {
					type: ComboBox,
					name: 'schools',
					label: _('School'),
					size: 'TwoThirds',
					staticValues: this.schools
				}],
				buttons: [{
					name: 'submit',
					label: _('Next')
				}],
				layout: [
					['headerText'],
					['schools', 'submit']
				]
			});
		},

		buildGrid: function() {
			var selectedSchool = array.filter(this.schools, lang.hitch(this, function(school) {
				return school.id === this._form.getWidget('schools').get('value');
			}))[0];
			var headerButtons = (this.schools.length > 1) ? [{
				name: 'changeSchool',
				label: _('Change school'),
				callback: lang.hitch(this, 'chooseDifferentSchool')
			}] : null;
			this.userGrid = new UserGrid({
				description: this.description,
				schools: [selectedSchool],
				school: selectedSchool.id,
				schoolLabel: selectedSchool.label,
				udmLinkEnabled: this.udmLinkEnabled,
				autoSearch: this.autoSearch,
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				moduleFlavor: this.moduleFlavor,
				module: this.module,
				headerButtons: headerButtons
			});

			// add UserGrid to module
			this.module.addChild(this.userGrid);
			this.module.selectChild(this.userGrid);

			// append title with the selected school
			this.module.addBreadCrumb(selectedSchool.label);
		},

		chooseDifferentSchool: function() {
			this.module.set('title', this.baseTitle);
			this.module.selectChild(this);
			this.module.removeChild(this.userGrid);
			this.userGrid.destroyRecursive();
		}
	});
});

