/*
 * SPDX-FileCopyrightText: 2012-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
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
	"umc/modules/schoolwizards/UserGridChooseSchool",
	"umc/modules/schoolwizards/ClassGrid",
	"umc/modules/schoolwizards/ComputerGrid",
	"umc/modules/schoolwizards/SchoolGrid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, all, topic, tools, dialog, Module, UserGridChooseSchool, ClassGrid, ComputerGrid, SchoolGrid, _) {
	var grids = {
		'schoolwizards/users': UserGridChooseSchool,
		'schoolwizards/classes': ClassGrid,
		'schoolwizards/computers': ComputerGrid,
		'schoolwizards/schools': SchoolGrid
	};

	return declare("umc.modules.schoolwizards", [Module], {

		_grid: null,
		schools: null,

		selectablePagesToLayoutMapping: {
			'_grid': 'searchpage-grid',
			'_grid.userGrid': 'searchpage-grid',
		},

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
			let ucrVariables = tools.ucr(['ucsschool/wizards/udmlink', 'ucsschool/wizards/autosearch', 'ucsschool/wizards/' + this.moduleFlavor + '/autosearch', 'ucsschool/wizards/autosearch_on_change', 'ucsschool/wizards/' + this.moduleFlavor + '/autosearch_on_change']).then(lang.hitch(this, lang.hitch(this, function(ucr) {
				this.autoSearch = tools.isTrue(ucr['ucsschool/wizards/' + this.moduleFlavor + '/autosearch'] || ucr['ucsschool/wizards/autosearch'] || true);
				this.autoSearchOnChange = tools.isTrue(ucr['ucsschool/wizards/' + this.moduleFlavor + '/autosearch_on_change'] || ucr['ucsschool/wizards/autosearch_on_change'] || true);
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
				autoSearchOnChange: this.autoSearchOnChange,
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				moduleFlavor: this.moduleFlavor,
				module: this
			});
		}
	});
});
