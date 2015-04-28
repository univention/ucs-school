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
	"umc/dialog",
	"umc/widgets/Module",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/SearchForm",
	"umc/modules/schoolgroups/WorkgroupDetailPage",
	"umc/modules/schoolgroups/ClassDetailPage",
	"umc/modules/schoolgroups/TeacherDetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, dialog, Module, Grid, Page, TextBox, ComboBox, SearchForm, WorkgroupDetailPage, ClassDetailPage, TeacherDetailPage, _) {
	var ModuleBase = declare("umc.modules.schoolgroups", [Module], {
		idProperty: '$dn$',
		_grid: null,
		_searchPage: null,
		_detailPage: null,
		standbyOpacity: 1,
		helpText: '',
		DetailPage: null,

		buildRendering: function() {
			this.inherited(arguments);

			this._searchPage = new Page({
				headerText: this.description,
				helpText: this.helpText
			});

			this.addChild(this._searchPage);

			this._grid = new Grid({
				actions: this.getGridActions(),
				columns: this.getGridColumns(),
				moduleStore: this.moduleStore
			});
			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				dynamicValues: 'schoolgroups/schools',
				label: _('School'),
				size: 'TwoThirds',
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				autoHide: true
			}, {
				type: TextBox,
				name: 'pattern',
				size: 'TwoThirds',
				description: _('Specifies the substring pattern which is searched for in the displayed name'),
				label: _('Search pattern')
			}];

			this._searchForm = new SearchForm({
				region: 'top',
				widgets: widgets,
				layout: [
					['school', 'pattern', 'submit']
				],
				onSearch: lang.hitch(this, function(values) {
					if (values.school) {
						this._grid.filter(values);
					}
				}),
				onValuesInitialized: lang.hitch(this, function() {
					this.standbyOpacity = 0.75;
					var values = this._searchForm.get('value');
					if (values.school) {
						this._grid.filter(values);
					}
			 	 })
			});
			this.standbyDuring(this._searchForm.ready());

			this._searchPage.addChild(this._searchForm);
			this._searchPage.startup();
		},

		createDetailPage: function() {
			var detailPage = new this.DetailPage({
				moduleStore: this.moduleStore,
				moduleFlavor: this.moduleFlavor,
				headerText: this.detailPageHeaderText,
				helpText: this.detailPageHelpText,
				schools: this._searchForm.getWidget('school').getAllItems(),
				umcpCommand: lang.hitch(this.moduleStore, 'umcpCommand')
			});
			this.addChild(detailPage);

			// connect to the onClose event of the detail page... we need to manage
			// visibility of sub pages here
			detailPage.on('close', lang.hitch(this, function() {
				this.selectChild(this._searchPage);
				this.removeChild(detailPage);
			}));
			this.own(detailPage);
			return detailPage;
		},

		getGridActions: function() {
			return [{
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected object'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}];
		},

		/*abstract*/getGridColumns: function() {
			return [];
		},

		_editObject: function(ids, items) {
			var detailPage = this.createDetailPage();
			detailPage.disableFields(true);
			this.selectChild(detailPage);
			detailPage.load(ids[0]);
		}
	});

	var Class = declare([ModuleBase], {
		DetailPage: ClassDetailPage,
		helpText: _('This module allows the maintenance of the membership of class groups. Teachers can be assigned or removed as group members.'),
		detailPageHeaderText: _('Edit class'),
		detailPageHelpText: _('This module allows the maintenance of the membership of class groups. Teachers can be assigned or removed as group members.'),
		getGridColumns: function() {
			return [{
				name: 'name',
				label: _('Name')
			}, {
				name: 'description',
				label: _('Description')
			}];
		}
	});

	var Teacher = declare([Class], {
		DetailPage: TeacherDetailPage,
		helpText: _('This module allows the maintenance of class memberships of teachers. The selected teacher can be added to one or multiple classes.'),
		detailPageHeaderText: _('Assigning of classes to a teacher'),
		detailPageHelpText: _('This module allows the maintenance of class memberships of teachers. The selected teacher can be added to one or multiple classes.'),
		getGridColumns: function() {
			return [{
				name: 'display_name',
				label: _('Name'),
				formatter: lang.hitch(this, function(nothing, id) {
					var item = this._grid.getRowValues(id);
					return '' + item.display_name + ' (' + item.name + ')';
				})
			}, {
				name: 'school_class',
				label: _('Class')
			}];
		}

	});

	var WorkGroup = declare([ModuleBase], {
		DetailPage: WorkgroupDetailPage,
		helpText: _('This module allows to modify class comprehensive workgroups. Arbitrary students and teacher of the school can be selected as group members.'),
		detailPageHeaderText: _('Edit workgroup'),
		detailPageHelpText: _('This module allows to modify class comprehensive workgroups. Arbitrary students and teacher of the school can be selected as group members.'),
		getGridColumns: function() {
			return [{
				name: 'name',
				label: _('Name')
			}, {
				name: 'description',
				label: _('Description')
			}];
		}
	});

	var WorkgroupAdmin = declare([WorkGroup], {
		helpText: _('This module allows to create, modify and delete class comprehensive workgroups. Arbitrary students and teacher of the school can be selected as group members.'),
		getGridActions: function() {
			var actions = this.inherited(arguments);

			actions.push({
				name: 'add',
				label: _('Add workgroup'),
				description: _('Create a new workgroup'),
				iconClass: 'umcIconAdd',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_addObject')
			});
			actions.push({
				name: 'delete',
				label: _('Delete'),
				description: _('Deleting the selected objects.'),
				isStandardAction: true,
				isMultiAction: false,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_deleteObjects')
			});
			return actions;
		},

		_addObject: function() {
			var detailPage = this.createDetailPage();
			detailPage._form.clearFormValues();

			detailPage.set('headerText', _('Add workgroup'));
			detailPage.set('school', this._searchForm.getWidget('school').get('value'));
			detailPage.disableFields(false);
			this.selectChild(detailPage);
		},

		_deleteObjects: function(ids, items) {
			dialog.confirm(lang.replace(_('Should the workgroup {name} be deleted?'), items[0]), [{
				name: 'cancel',
				'default': true,
				label: _('Cancel')
			}, {
				name: 'delete',
				label: _('Delete')
			}]).then(lang.hitch(this, function(action) {
				if (action != 'delete') {
					// action canceled
					return;
				}
				this.standbyDuring(this.moduleStore.remove(ids)).then(lang.hitch(this, function(response) {
					if (response.success === true) {
						dialog.alert(_('The workgroup has been deleted successfully'));
					} else {
						dialog.alert(lang.replace(_('The workgroup could not be deleted ({message})'), response));
					}
				}));
			}));
		}
	});

	return {
		load: function (flavor, req, load, config) {
			load({
				'class': Class,
				'teacher': Teacher,
				'workgroup': WorkGroup,
				'workgroup-admin': WorkgroupAdmin
			}[flavor]);
		}
	};
});
