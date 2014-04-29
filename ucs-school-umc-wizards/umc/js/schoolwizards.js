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
	"dojo/promise/all",
	"umc/tools",
	"umc/widgets/Module",
	"umc/modules/schoolwizards/UserGrid",
	"umc/modules/schoolwizards/ClassGrid",
	"umc/modules/schoolwizards/ComputerGrid",
	"umc/modules/schoolwizards/SchoolGrid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, all, tools, Module, UserGrid, ClassGrid, ComputerGrid, SchoolGrid, _) {
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
			var schools = this.umcpCommand('schoolwizards/schools', {'all_option_if_appropriate' : true}).then(lang.hitch(this, function(data) {
				this.schools = data.result;
			}));
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
