/*
 * Copyright 2012-2016 Univention GmbH
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
	"umc/widgets/Form",
	"umc/widgets/Page",
	"umc/widgets/Button",
	"umc/widgets/ComboBox",
	"umc/widgets/Text",
	"umc/modules/schoolwizards/UserGrid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, Form, Page, Button, ComboBox, Text, UserGrid, _) {

	return declare("umc.modules.schoolwizards.UserGridChooseSchool", [Page], {
		userGrid: null,
		baseTitle: null,
		_form: null,

		postMixInProperties: function() {
			this.baseTitle = this.module.get('title');
		},

		buildRendering: function() {
			this.inherited(arguments);

			var headerTextWidget = this.createHeader();
			this._form = this.createForm();
			this._form.on('submit', lang.hitch(this, 'buildGrid'));

			this.addChild(headerTextWidget);
			this.addChild(this._form);
			if (this.schools.length <= 1) {
				this.buildGrid();
			}
		},

		createHeader: function() {
			var headerText = _("Select a school on which you like to work on");
			return new Text({
				content: _('<h1>' + headerText + '<h1>'),
				'class': 'umcPageHeader'
			});
		},

		createForm: function() {
			return new Form({
				widgets: [{
					type: ComboBox,
					name: 'schools',
					label: _('School'),
					size: 'OneThirds',
					staticValues: this.schools
				}],
				buttons: [{
					name: 'submit',
					label: _('Next')
				}],
				layout: [
					['schools', 'submit']
				]
			});
		},

		buildGrid: function() {
			var selectedSchool = array.filter(this.schools, lang.hitch(this, function(school) {
				return school.id === this._form.getWidget('schools').get('value');
			}))[0];
			var _backToSchool = new Button({
				name: 'back',
				label: _('Back'),
				region: 'footer',
				onClick: lang.hitch(this, 'chooseDifferentSchool')
			});
			var userGrid = new UserGrid({
				description: this.description,
				schools: [selectedSchool],
				udmLinkEnabled: this.udmLinkEnabled,
				autoSearch: this.autoSearch,
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				moduleFlavor: this.moduleFlavor,
				module: this.module
			});

			// add UserGrid to module
			if (this.schools.length > 1) {
				userGrid.addChild(_backToSchool);
			}
			this.module.addChild(userGrid);
			this.module.selectChild(userGrid);

			// append title with the selected school
			var titleAppendix = lang.replace(": {0}", [selectedSchool.label]);
			this.module.set('title', this.baseTitle + titleAppendix);

			this.userGrid = userGrid;
		},

		chooseDifferentSchool: function() {
			this.module.set('title', this.baseTitle);
			this.module.selectChild(this);
			this.module.removeChild(this.userGrid);
			this.userGrid.destroyRecursive();
		}
	});
});

