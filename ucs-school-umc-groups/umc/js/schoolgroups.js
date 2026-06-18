/*
 * SPDX-FileCopyrightText: 2012-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojox/html/entities",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Module",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/SearchBox",
	"umc/widgets/ComboBox",
	"umc/widgets/SearchForm",
	"umc/widgets/Text",
	"umc/widgets/Tooltip",
	"umc/modules/schoolgroups/WorkgroupDetailPage",
	"umc/modules/schoolgroups/ClassDetailPage",
	"umc/modules/schoolgroups/TeacherDetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, array, entities, tools, dialog, Module, Grid, Page, SearchBox, ComboBox, SearchForm, Text, Tooltip, WorkgroupDetailPage, ClassDetailPage, TeacherDetailPage, _) { // eslint-disable-line max-params
	// language-aware sort; numeric so '2a' sorts before '10a'
	// eslint-disable-next-line unicorn/consistent-function-scoping -- AMD module: define() callback is already the highest scope
	function localeSort(a, b) {
		return a.localeCompare(b, undefined, {numeric: true});
	}

	// drop the redundant '<school>-' prefix; the school is shown as the group label
	function stripSchoolPrefix(school_classes, school) {
		return array.map(school_classes, function(value) {
			return value.includes(school + '-') ? value.slice(school.length + 1) : value;
		});
	}

	var ModuleBase = declare("umc.modules.schoolgroups", [Module], {
		idProperty: '$dn$',
		_grid: null,
		_searchPage: null,
		_detailPage: null,
		helpText: '',
		mailAddressPattern: '',
		// UCR variable that controls the automatic search when the module is opened.
		autosearchVariable: '',
		autoSearch: true,
		// UCR variable that controls the automatic search when the selected school
		// is changed. Configurable independently because the initial search is often
		// performed on the wrong school (the first one), so customers want to disable
		// it without disabling the search on an explicit school change.
		autosearchOnChangeVariable: '',
		autoSearchOnChange: true,
		DetailPage: null,
		// whether more than one row may be selected in the grid; only useful
		// for flavors that offer a multi action (e.g. delete).
		multiSelect: false,

		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid'
		},

		buildRendering: function() {
			this.inherited(arguments);

			this.standbyDuring(tools.ucr([this.autosearchVariable, this.autosearchOnChangeVariable, 'ucsschool/workgroups/mailaddress'])).then(lang.hitch(this, function(vars) {
				this.autoSearch = tools.isTrue(vars[this.autosearchVariable] || this.autoSearch);
				this.autoSearchOnChange = tools.isTrue(vars[this.autosearchOnChangeVariable] || this.autoSearchOnChange);
				this.mailAddressPattern = vars['ucsschool/workgroups/mailaddress'] || '';
				this.renderSearchForm();
			}));
		},

		renderSearchForm: function() {

			this._searchPage = new Page({
				fullWidth: true,
				headerText: this.description,
				helpText: this.helpText
			});

			this.addChild(this._searchPage);

			this._grid = new Grid({
				actions: this.getGridActions(),
				columns: this.getGridColumns(),
				gridOptions: this.multiSelect ? {} : {selectionMode: 'single'},
				moduleStore: this.moduleStore,
				hideContextActionsWhenNoSelection: false,
				allowHTML: false
			});
			this._searchPage.addChild(this._grid);

			if (!this.multiSelect) {
				let innerGrid = this._grid._grid;

				// The "select all" header checkbox makes no sense with single selection.
				// Setting allowSelectAll: false would drop it, but that breaks the header
				// layout (dgrid then renders the column label instead), so just disable the
				// rendered checkbox.
				let selectorColumn = innerGrid._selectorColumns[0];
				if (selectorColumn?._selectorHeaderCheckbox) {
					selectorColumn._selectorHeaderCheckbox.$checkbox.set('disabled', true);
				}

				// dgrid only enforces selectionMode 'single' for clicks on the row body,
				// not for the checkboxes of the selector column: those toggle the selection
				// directly and bypass the single-selection handling. Enforce it manually by
				// deselecting any previously selected row whenever a new row gets selected.
				innerGrid.on('dgrid-select', lang.hitch(this, function(evt) {
					let keepId = String(evt.rows[evt.rows.length - 1].id);
					array.forEach(innerGrid.getSelectedIDs(), function(id) {
						if (String(id) !== keepId) {
							innerGrid.deselect(id);
						}
					});
				}));
			}

			var widgets = [{
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
				name: 'school',
				dynamicValues: 'schoolgroups/schools',
				label: _('School'),
				size: 'TwoThirds',
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				autoHide: true,
				onChange: lang.hitch(this, function() {
					// trigger the search on an explicit school change. The guard skips the
					// onChange that fires while the form is still being initialized; the
					// initial search is handled by onValuesInitialized (and gated by the
					// separate 'autosearch' variable).
					if (this._valuesInitialized && this.autoSearchOnChange) {
						this._search();
					}
				})
			}, {
				type: SearchBox,
				'class': 'umcTextBoxOnBody',
				name: 'pattern',
				size: 'TwoThirds',
				description: _('Specifies the substring pattern which is searched for in the displayed name'),
				label: _('Search pattern'),
				inlineLabel: _('Search...'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];

			this._searchForm = new SearchForm({
				region: 'top',
				hideSubmitButton: true,
				widgets: widgets,
				layout: [
					['school', 'pattern']
				],
				onSearch: lang.hitch(this, function(values) {
					if (values.school) {
						this._grid.filter(values);
					}
				}),
				onValuesInitialized: lang.hitch(this, function() {
					this._valuesInitialized = true;
					if (this.autoSearch) {
						this._search();
					}
				})
			});
			this.standbyDuring(this._searchForm.ready());

			this._searchPage.addChild(this._searchForm);
			this._searchPage.startup();
		},

		_search: function() {
			let values = this._searchForm.get('value');
			if (values.school) {
				this._grid.filter(values);
			}
		},

		createDetailPage: function() {
			var detailPage = new this.DetailPage({
				moduleStore: this.moduleStore,
				moduleFlavor: this.moduleFlavor,
				headerText: this.detailPageHeaderText,
				helpText: this.detailPageHelpText,
				schools: this._searchForm.getWidget('school').getAllItems(),
				umcpCommand: lang.hitch(this.moduleStore, 'umcpCommand'),
				mailAddressPattern: this.mailAddressPattern
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
				iconClass: 'edit-2',
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
			detailPage.set('school', this._searchForm.getWidget('school').get('value'));
			detailPage.disableFields(true);
			detailPage.setupEditMode();
			this.selectChild(detailPage);
			detailPage.load(ids[0]);
		}
	});

	var Class = declare([ModuleBase], {
		autosearchVariable: 'ucsschool/assign-teachers/autosearch',
		autosearchOnChangeVariable: 'ucsschool/assign-teachers/autosearch_on_change',
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
		autosearchVariable: 'ucsschool/assign-classes/autosearch',
		autosearchOnChangeVariable: 'ucsschool/assign-classes/autosearch_on_change',
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
				name: 'school_classes',
				label: _('Class'),
				formatter: lang.hitch(this, function(values, id, all_values) {
					let cellGroups = [];
					let tooltipGroups = [];
					let schools = [];
					tools.forIn(values, function(school) {
						schools.push(school);
					});
					schools.sort(localeSort);
					array.forEach(schools, function(school) {
						let school_classes = values[school];
						let sortedClasses = school_classes.slice().sort(localeSort);
						let groupedClasses = stripSchoolPrefix(sortedClasses, school).join(', ');
						// same grouping in the cell (single line, truncated with an ellipsis)
						// and in the tooltip (one group per line, school in bold)
						cellGroups.push(entities.encode(school) + ': ' + entities.encode(groupedClasses));
						tooltipGroups.push('<b>' + entities.encode(school) + ':</b> ' + entities.encode(groupedClasses));
					});

					let widget = new Text({
						content: cellGroups.join('; ')
					});
					this.own(widget);

					if (tooltipGroups.length) {
						let tooltip = new Tooltip({
							label: tooltipGroups.join('<br>'),
							connectId: [widget.domNode],
							position: ['below', 'above']
						});
						widget.own(tooltip);
					}
					return widget;
				})
			}];
		}

	});

	var WorkGroup = declare([ModuleBase], {
		autosearchVariable: 'ucsschool/workgroups/autosearch',
		autosearchOnChangeVariable: 'ucsschool/workgroups/autosearch_on_change',
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
		// keep multi selection here, the delete action operates on multiple objects
		multiSelect: true,
		helpText: _('This module allows to create, modify and delete class comprehensive workgroups. Arbitrary students and teacher of the school can be selected as group members.'),
		getGridActions: function() {
			var actions = this.inherited(arguments);

			actions.push({
				name: 'add',
				label: _('Add workgroup'),
				description: _('Create a new workgroup'),
				iconClass: 'plus',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_addObject')
			});
			actions.push({
				name: 'delete',
				label: _('Delete'),
				description: _('Deleting the selected objects.'),
				isStandardAction: true,
				isMultiAction: true,
				iconClass: 'trash',
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
			dialog.confirm(_('Should the selected workgroups be deleted?'), [{
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
						dialog.alert(_('The workgroups have been deleted successfully'));
					} else {
						dialog.alert(lang.replace(_('The workgroups could not be deleted ({message})'), {message: entities.encode(response.message)}));
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
