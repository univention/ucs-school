/*
 * Copyright 2012-2015 Univention GmbH
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
	"dojo/promise/all",
	"dojo/topic",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Module",
	"umc/modules/schoolwizards/UserGrid",
	"umc/modules/schoolwizards/ClassGrid",
	"umc/modules/schoolwizards/ComputerGrid",
	"umc/modules/schoolwizards/SchoolGrid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, all, topic, tools, dialog, Module, UserGrid, ClassGrid, ComputerGrid, SchoolGrid, _) {
	var grids = {
		'schoolwizards/users': UserGrid,
		'schoolwizards/classes': ClassGrid,
		'schoolwizards/computers': ComputerGrid,
		'schoolwizards/schools': SchoolGrid
	};

	return declare("umc.modules.schoolwizards", [Module], {

		_grid: null,
		schools: null,

		buildRendering: function() {
			this.inherited(arguments);
			var schools = this.umcpCommand('schoolwizards/schools', {}, false).then(
				lang.hitch(this, function(data) {
					this.schools = data.result;
					this.schools.sort(tools.cmpObjects({
						attribute: 'label',
						ignoreCase: true
					}));
				}),
				lang.hitch(this, function() {
					this.schools = [];
					// error. most probably no schools found
					if (this.moduleFlavor == 'schoolwizards/schools') {
						// goto school grid. no need for error message
						return;
					}
					var txt = _('No school could be found within the domain. Before students, classes, and computers can be administrated, at least one school has to be created.');
					txt = txt + '<br />' + _('The module for administrating schools will be opened.');
					dialog.confirm(txt, [{
						name: 'submit',
						'default': true,
						label: _('Create school')
					}], _('No school found')).then(lang.hitch(this, function(response) {
						topic.publish('/umc/modules/open', 'schoolwizards', 'schoolwizards/schools');
						topic.publish('/umc/tabs/close', this);
					}));
				})
			);
			var ucrVariables = tools.ucr(['ucsschool/wizards/udmlink', 'ucsschool/wizards/autosearch', 'ucsschool/wizards/' + this.moduleFlavor + '/autosearch']).then(lang.hitch(this, lang.hitch(this, function(ucr) {
				this.autoSearch = tools.isTrue(ucr['ucsschool/wizards/' + this.moduleFlavor + '/autosearch'] || ucr['ucsschool/wizards/autosearch'] || true);
				var udmLink = ucr['ucsschool/wizards/udmlink'];
				this.udmLinkEnabled = udmLink === null || tools.isTrue(udmLink);
			})));
			var preparation = all([schools, ucrVariables]);
			this.standbyDuring(preparation);
			preparation.then(lang.hitch(this, function() {
				this._grid = this._getGrid();
				this.addChild(this._grid);
			}));
		},

		_getGrid: function() {
			var Grid = grids[this.moduleFlavor];

			return new Grid({
				description: this.description,
				schools: this.schools,
				udmLinkEnabled: this.udmLinkEnabled,
				autoSearch: this.autoSearch,
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				moduleFlavor: this.moduleFlavor,
				module: this
			});
		}
	});
});
