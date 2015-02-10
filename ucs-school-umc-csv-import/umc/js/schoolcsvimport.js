/*
 * Copyright 2014-2015 Univention GmbH
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
	"dojo/query",
	"dojo/topic",
	"dojo/when",
	"dojo/on",
	"dojo/Deferred",
	"dojo/store/Memory",
	"dojo/_base/window",
	"dojo/dom-construct",
	"dojo/dom-style",
	"dojo/dom-attr",
	"dojo/dom-geometry",
	"dojo/date/locale",
	"dijit/Menu",
	"dijit/CheckedMenuItem",
	"dojox/timing/_base",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Text",
	"umc/widgets/TextBox",
	"umc/widgets/Form",
	"umc/widgets/ProgressBar",
	"umc/widgets/ComboBox",
	"umc/widgets/Uploader",
	"umc/widgets/CheckBox",
	"umc/widgets/Wizard",
	"umc/modules/schoolcsvimport/DateBox",
	"umc/modules/schoolcsvimport/Grid",
	"umc/widgets/Module",
	"umc/modules/schoolcsvimport/User",
	"umc/i18n!umc/modules/schoolcsvimport"
], function(declare, lang, array, query, topic, when, on, Deferred, Memory, win, construct, style, attr, geometry, dateLocaleModule, Menu, CheckedMenuItem, timing, tools, dialog, Text, TextBox, Form, ProgressBar, ComboBox, Uploader, CheckBox, Wizard, DateBox, Grid, Module, User, _) {
	var UploadWizard = declare('umc.modules.schoolcsvimport.Wizard', Wizard, {
		autoValidate: true,

		postMixInProperties: function() {
			this.inherited(arguments);
			this.pages = [{
				name: 'general',
				headerText: this.description,
				helpText: _('This assistant guides through the individual steps for importing UCS@school users with a CSV file. At first, the user role for the users from the CSV file needs to be specified.'),
				widgets: [{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					dynamicValues: 'schoolcsvimport/schools',
					autoHide: true,
					required: true
				}, {
					type: ComboBox,
					name: 'type',
					label: _('User role'),
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
				}]
			}, {
				name: 'upload',
				headerText: this.description,
				helpText: _('Please upload the CSV file. The CSV file has to contain comma separated values. A "header line" helps with the assignment of the individual columns after uploading. This line is optional.'),
				widgets: [{
					type: Text,
					name: 'csv_help',
					content: _('Example of a CSV file:') +
						'<pre>' +
							lang.replace('{username},{firstname},{lastname},{birthday}', {
								username: _('Username'),
								firstname: _('First name'),
								lastname: _('Last name'),
								birthday: _('Birthday')}) + '\n' +
							_('john.doe,Johnathan James,Doe,03/15/2000') + '\n' +
							'[...]' +
						'</pre>'
				}, {
					type: CheckBox,
					name: 'delete_not_mentioned',
					label: _('Replacement of the existing users of the selected user role with the users in the CSV file. This means that all users not included in the CSV file will be deleted.')
				}, {
					type: Uploader,
					name: 'file',
					label: _('Upload file'),
					command: 'schoolcsvimport/save',
					dynamicOptions: lang.hitch(this, 'getUploaderParams'),
					onUploadStarted: lang.hitch(this, function() {
						this.standby(true);
					}),
					onUploaded: lang.hitch(this, function(result) {
						this.standby(false);
						if (typeof result == "string" || !result.success) {
							// Apache gateway timeout error or
							// CSV error
							dialog.alert(_('The file provided could not be used as a CSV file. Please check the format.'));
							return;
						}
						this.fileID = result.file_id;
						var availableColumns = result.available_columns;
						var givenColumns = result.given_columns;
						var users = [];
						array.forEach(result.first_lines, function(csvLine) {
							var user = {};
							array.forEach(csvLine, function(attr, j) {
								user[givenColumns[j]] = attr;
							});
							users.push(user);
						});
						if (result.num_more_lines) {
							var fakeUser = {};
							fakeUser[givenColumns[0]] = _('%d more lines...', result.num_more_lines);
							users.push(fakeUser);
						}
						givenColumns = array.map(givenColumns, function(column) {
							var givenColumn = null;
							var originalColumn = column;
							if ((/^unused.*/).test(column)) {
								// search for "unused" in availableColumns
								// but preserve "unused2" as name
								column = 'unused';
							}
							array.forEach(availableColumns, function(columnDefinition) {
								if (columnDefinition.name == column) {
									givenColumn = lang.clone(columnDefinition);
									givenColumn.name = originalColumn;
								}
							});
							return givenColumn;
						});
						var page = this.getPage('assign');
						page._grid = this.addGridAssign(page, availableColumns, givenColumns, users);
						this._next('upload');
					})
				}]
			}, {
				name: 'assign',
				headerText: this.description,
				helpText: _('In the table below the first 10 lines of the CSV file are shown. It is necessary for the import to assign the individual columns concrete data types (first name, last name, ...). By clicking on the header line of the table the corresponding data type for each column can be chosen. At least first name and last name need to be given for the import to be successful.')
			}, {
				name: 'spreadsheet',
				headerText: this.description,
				helpText: _('The CSV file was matched with the existing data. The individual lines show the user modifications, problems are highlighted in color. The individual lines can be edited via the button "Edit" or by clicking on the value of the first column "Action".')
			}, {
				name: 'finished',
				headerText: this.description,
				helpText: _('Import finished.'),
				widgets: [{
					type: Text,
					name: 'errors',
					content: _('The import has been successfully completed.')
				}]
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);
			var widget = this.getWidget('upload', 'delete_not_mentioned');
			query('.umcLabelPaneLabeNodeRight', widget.$refLabel$.domNode).style('display', 'inline');
			query(widget.$refLabel$.domNode).style({marginBottom: '1.5em', marginTop: '1.5em'});
		},

		next: function(pageName) {
			var nextPage = this.inherited(arguments);
			var page = this.getPage(pageName);
			var deferred = new Deferred();
			var grid;
			if (pageName == 'assign') {
				this.getWidget('spreadsheet', 'show_errors').set('value', false);
				grid = page._grid._grid;
				var structure = grid.get('structure');
				var cells = array.map(structure, function(struct) { return grid.getCellByField(struct.field); });
				var fields = array.map(cells, function(cell) { return cell._usedAs || null; });
				if (array.indexOf(fields, 'firstname') == -1 || array.indexOf(fields, 'lastname') == -1) {
					dialog.alert(_('You need to specify at least "%(firstname)s" and "%(lastname)s" as columns. Click on the column header in the table', {firstname: _('First name'), lastname: _('Last name')}));
					deferred.reject();
					return deferred;
				}
				var auto_username = false;
				if (array.indexOf(fields, 'name') == -1) {
					auto_username = true;
				}
				if (auto_username) {
					dialog.confirm(_('No column was chosen as username. The system can generate a username for new users resp. try to find the user among the existing users in the database.', {username: _('Username')}), [{
						label: _('Back'),
						name: 'cancel',
						'default': true
					}, {
						label: _('Automatically identify username'),
						name: 'continue'
					}]).then(
						function(response) {
							if (response == 'continue') {
								deferred.resolve(nextPage);
							}
							deferred.reject();
						},
						function() {
							deferred.reject();
						}
					);
				} else {
					deferred.resolve(nextPage);
				}
				return deferred.then(lang.hitch(this, function(nextPage) {
					this.progressBar.reset();
					var showing = tools.umcpProgressCommand(this.progressBar, 'schoolcsvimport/show', {file_id: this.fileID, columns: fields}).then(
						lang.hitch(this, function(result) {
							var page = this.getPage('spreadsheet');
							this.datePattern = result.date_pattern;
							this.requiredColumns = result.required_columns;
							page._grid = this.addGridSpreadSheet(page, result.columns, result.users);
							if (result.license_error) {
								return dialog.confirm(result.license_error, [{
									name: 'cancel',
									'default': true,
									label: _('Cancel')
								}, {
									name: 'continue',
									label: _('Continue')
								}], _('Error while validating the license')).then(function(response) {
									if (response == 'continue') {
										return nextPage;
									} else {
										return 'upload';
									}
								});
							} else {
								return nextPage;
							}
						}));
					return this.standbyDuring(showing, this.progressBar);
				}));
			} else if (pageName == 'spreadsheet') {
				grid = page._grid;
				var items = grid.moduleStore.data;
				var params = [];
				var nAdd = 0, nMod = 0, nDel = 0, nIgn = 0;
				var unresolvedErrors = false;
				array.forEach(items, lang.hitch(this, function(item) {
					var action = item.action;
					if (action == 'create') {
						nAdd += 1;
					} else if (action == 'modify') {
						nMod += 1;
					} else if (action == 'delete') {
						nDel += 1;
					} else {
						nIgn += 1;
					}
					if (action != 'ignore') {
						if (!tools.isEqual(item.errors, {})) {
							unresolvedErrors = true;
						}
						params.push({file_id: this.fileID, attrs: item.toObject()});
					}
				}));
				if (unresolvedErrors) {
					dialog.alert(_('There are still unresolved errors in the file. You need to correct the red lines before continuing.'));
					deferred.reject();
					return deferred;
				}
				dialog.confirm(_('Please confirm the following changes:') +
					'<ul><li>' +
						_('%s user(s) will be added', nAdd) +
					'</li><li>' +
						_('%s user(s) will be modified', nMod) +
					'</li><li>' +
						(nDel ? '<strong>' : '') +
						_('%s user(s) will be deleted', nDel) +
						(nDel ? '</strong>' : '') +
					'</li><li>' +
						_('%s user(s) will be ignored', nIgn) +
					'</li></ul>', [{
					label: _('Cancel'),
					name: 'cancel'
				}, {
					label: _('Confirm changes'),
					name: 'continue',
					'default': true
				}]).then(
					lang.hitch(this, function(response) {
						if (response == 'continue') {
							this.progressBar.reset();
							var importing = tools.umcpProgressCommand(this.progressBar, 'schoolcsvimport/import', params).then(
								lang.hitch(this, function(result) {
									var errors = [];
									array.forEach(result, function(iresult) {
										if (!iresult.success) {
											errors.push(iresult.msg);
										}
									});
									if (errors.length) {
										var widget = this.getWidget('finished', 'errors');
										var errorMessage = _('%d error(s) occurred:', errors.length);
										errorMessage = errorMessage + '<ul><li>' + errors.join('</li><li>') + '</li></ul>';
										widget.set('content', errorMessage);
									}
									deferred.resolve(nextPage);
								}), function() {
									deferred.reject();
								}
							);
							this.standbyDuring(importing, this.progressBar);
						} else {
							deferred.reject();
						}
					}),
					function() {
						deferred.reject();
					}
				);
			} else {
				deferred.resolve(nextPage);
			}
			return deferred;
		},

		getUploaderParams: function() {
			var school = this.getWidget('general', 'school').get('value');
			var type = this.getWidget('general', 'type').get('value');
			var params = {school: school, type: type};
			var delete_not_mentioned = this.getWidget('upload', 'delete_not_mentioned').get('value');
			if (delete_not_mentioned) {
				// only put it here when set. false will go into body and is then
				// translated to string "false" in python which evaluates to True...
				params.delete_not_mentioned = delete_not_mentioned;
			}
			return params;
		},

		addMenuItem: function(headerMenu, label, name) {
			var updateGridField = lang.hitch(this, 'updateGridField');
			headerMenu.addChild(new CheckedMenuItem({
				label: label,
				name: name,
				onClick: function() {
					if (this._headerCell) {
						var unused = 'unused';
						var unusedLabel = _('Unused');
						var fieldName = this.get('name');
						var fieldLabel = this.get('label');
						if (!this.get('checked')) {
							fieldName = unused;
							fieldLabel = unusedLabel;
						}
						var grid = this._headerCell.grid;
						var myField = this._headerCell.field;
						updateGridField(grid, myField, fieldName, fieldLabel, unusedLabel);
						grid.update();
					}
				}
			}));
		},

		updateGridField: function(grid, myField, fieldName, fieldLabel, unusedLabel) {
			array.forEach(grid.get('structure'), function(struct) {
				var columnNode = grid.getCellByField(struct.field);
				if (columnNode.field == myField) {
					columnNode._usedAs = fieldName;
					columnNode.name = fieldLabel;
				} else if (columnNode.name == fieldLabel) {
					delete columnNode._usedAs;
					columnNode.name = unusedLabel;
				}
			});
		},

		addGridAssign: function(parentWidget, availableColumns, givenColumns, users) {
			if (parentWidget._grid) {
				parentWidget.removeChild(parentWidget._grid);
				parentWidget._grid.destroyRecursive();
			}
			array.forEach(givenColumns, lang.hitch(this, function(column) {
				var attributes = [column.label].concat(array.map(users, function(user) { return user[column.name]; }));
				column.width = this._getWidth(attributes) + 'px';
				column.noresize = true;
				column.defaultValue = '';
			}));
			var headerMenu = new Menu({
				leftClickToOpen: true
			});
			this.own(headerMenu);
			array.forEach(availableColumns, lang.hitch(this, function(columnDefinition) {
				this.addMenuItem(headerMenu, columnDefinition.label, columnDefinition.name);
			}));
			users = array.map(users, function(user) {
				return new User(user);
			});
			var dataStore = new Memory({
				data: users
			});
			var grid = new Grid({
				region: 'center',
				moduleStore: dataStore,
				columns: givenColumns,
				footerFormatter: function() { return ''; },
				_updateContextItem: function() {},
				_onRowClick: function() {},
				gridOptions: {
					selectionMode: 'none',
					canSort: function() {
						return false;
					},
					plugins: {
						menus: {
							headerMenu: headerMenu
						}
					}
				}
			});
			array.forEach(givenColumns, lang.hitch(this, function(columnDefinition) {
				this.updateGridField(grid._grid, columnDefinition.name, columnDefinition.name, columnDefinition.label, _('Unused'));
			}));
			grid._grid.on('HeaderCellContextMenu', lang.hitch(headerMenu, function(e) {
				var menuItems = this.getChildren();
				array.forEach(menuItems, function(menuItem) {
					var target = e.cell;
					menuItem._headerCell = target;
					menuItem.set('checked', target.name == menuItem.get('label'));
				});
			}));
			grid._grid.on('headerCellClick', lang.hitch(grid._grid, function(e) {
				this.doheadercontextmenu(e);
			}));
			parentWidget.addChild(grid);
			parentWidget._grid = grid;
			grid._grid.update();
			query('.dojoxGridScrollbox', grid.domNode).style('overflowX', 'auto');
			return grid;
		},

		_getWidth: function(texts) {
			// if we do not have a temporary cell yet, create it
			if (!this._tmpCell && !this._tmpCellHeader) {
				this._tmpCellHeader = construct.create('div', { 'class': 'dojoxGridHeader dijitOffScreen' });
				this._tmpCell = construct.create('div', { 'class': 'dojoxGridCell' });
				construct.place(this._tmpCell, this._tmpCellHeader);
				construct.place(this._tmpCellHeader, win.body());
			}

			var maxWidth = 0;
			var width;
			array.forEach(texts, lang.hitch(this, function(text, idx) {
				// set the text
				attr.set(this._tmpCell, 'innerHTML', text);

				// get the width of the cell
				width = geometry.getMarginBox(this._tmpCell).w;
				if (idx === 0) {
					width += 18; // sort arrow
				}
				if (width > maxWidth) {
					maxWidth = width;
				}
			}));
			return maxWidth;
		},

		addGridSpreadSheet: function(parentWidget, columns, users) {
			if (parentWidget._grid) {
				parentWidget.removeChild(parentWidget._grid);
				parentWidget._grid.destroyRecursive();
			}
			array.forEach(columns, lang.hitch(this, function(column) {
				var attributes = [column.label].concat(array.map(users, function(user) { return user[column.name]; }));
				column.width = this._getWidth(attributes) + 'px';
				column.noresize = true;
				column.defaultValue = '';
				if (column.name == 'action') {
					column.formatter = function(value) {
						var actionMap = {
							'delete' : _('Delete'),
							'create' : _('Create'),
							'modify' : _('Modify'),
							'ignore' : _('Ignore')
						};
						return actionMap[value];
					};
				}
			}));
			users = array.map(users, function(user) {
				return new User(user);
			});
			var dataStore = new Memory({
				data: users
			});
			var grid = new Grid({
				region: 'center',
				moduleStore: dataStore,
				actions: [{
					name: 'edit',
					label: _('Edit'),
					description: _('Edit this line'),
					iconClass: 'umcIconEdit',
					isStandardAction: true,
					isContextAction: true,
					callback: lang.hitch(this, function(ids, items) {
						var grid = this.getPage('spreadsheet')._grid;
						array.forEach(items, lang.hitch(this, function(item) {
							this.openEditDialog(item, grid);
						}));
					})
				}, {
					name: 'ignore',
					label: _('Ignore'),
					description: _('Ignore the selected lines'),
					isMultiAction: true,
					isStandardAction: true,
					isContextAction: true,
					callback: lang.hitch(this, function(ids, items) {
						var itemObjs = [];
						array.forEach(items, function(item) {
							item.action = 'ignore';
						});
						this.checkThemAll(grid);
					})
				}, {
					name: 'reset',
					label: _('Reset'),
					description: _('Restore initial values from the uploaded file'),
					isMultiAction: true,
					isStandardAction: true,
					isContextAction: true,
					callback: lang.hitch(this, function(ids, items) {
						var itemObjs = [];
						array.forEach(items, function(item) {
							item.restore();
							itemObjs.push(item.toObject());
						});
						var recheck = tools.umcpCommand('schoolcsvimport/recheck', {file_id: this.fileID, user_attrs: itemObjs}).then(lang.hitch(this, function(data) {
							array.forEach(data.result, function(recheckedItem, i) {
								var item = items[i];
								item._initialValues.warnings = recheckedItem.warnings;
								item._initialValues.errors = recheckedItem.errors;
							});
							this.checkThemAll(grid);
						}));
						this.standbyDuring(recheck);
					})
				}],
				columns: columns
			});
			grid._grid.on('StyleRow', function(row) {
				var item = this.getItem(row.index);
				if (item) {
					item.styleError(this, row);
				}
			});
			grid._grid.on('cellDblClick', lang.hitch(this, function(e) {
				var cell = e.cell;
				var grid = this.getPage('spreadsheet')._grid;
				var item = grid._grid.getItem(e.rowIndex);
				this.openEditDialog(item, grid, cell.field);
			}));
			this.checkThemAll(grid);
			var lineIdx = grid._grid.getCellByField('line').index + 1;
			grid._grid.setSortIndex(lineIdx);
			parentWidget.addChild(grid);
			parentWidget._grid = grid;
			query('.dojoxGridScrollbox', grid.domNode).style('overflowX', 'auto');
			return grid;
		},

		checkThemAll: function(grid) {
			var assertUniqueness = function(users, field, errorMessage, grid) {
				var column = grid.getCellByField(field);
				if (!column) {
					return;
				}
				var values = [];
				var doubles = [];
				array.forEach(users, function(item) {
					if (item.action == 'ignore') {
						return;
					}
					var value = item[field];
					if (!value) {
						return;
					}
					if (array.indexOf(doubles, value) !== -1) {
						return;
					}
					if (array.indexOf(values, value) !== -1) {
						doubles.push(value);
						return;
					}
					values.push(value);
				});
				array.forEach(doubles, function(value) {
					array.forEach(users, function(item) {
						if (item[field] == value) {
							item.setError(field, errorMessage, grid);
						}
					});
				});
			};
			var items = grid.moduleStore.data;
			var dateConstraints = {datePattern: this.datePattern, selector: 'date'};
			array.forEach(items, function(item) {
				item.resetError();
				if (item.action == 'ignore') {
					return;
				}
				var birthdayColumnExists = array.some(grid._grid.get('structure'), function(struct) {
					return struct.field == 'birthday';
				});
				if (birthdayColumnExists) {
					var birthday = item.birthday;
					if (birthday) {
						var parsedDate = dateLocaleModule.parse(birthday, dateConstraints);
						if (!parsedDate) {
							item.setError('birthday', _('The birthday does not follow the format for dates. Please change the birthday.'), grid._grid);
						}
					}
				}
			});
			assertUniqueness(items, 'name', _('Username occurs multiple times in the file. Please change the usernames so that all are unique.'), grid._grid);
			assertUniqueness(items, 'email', _('Email address occurs multiple times in the file. Please change the email adresses so that all are unique.'), grid._grid);
			grid._grid.update();
		},

		openEditDialog: function(item, grid, focusWidget) {
			var widgets = [];
			var form;
			array.forEach(grid._grid.get('structure'), lang.hitch(this, function(struct) {
				var key = struct.field;
				var value = item[key];
				if (key == 'line') {
					return;
				}
				var type = TextBox;
				var staticValues = null;
				var datePattern = null;
				var required = array.indexOf(this.requiredColumns, key) !== -1;
				if (key == 'birthday') {
					type = DateBox;
					datePattern = this.datePattern;
				}
				if (key == 'action') {
					type = ComboBox;
					staticValues = [{id: 'create', label: _('Create')}, {id: 'modify', label: _('Modify')}, {id: 'delete', label: _('Delete')}, {id: 'ignore', label: _('Ignore')}];
				}
				var label = grid._grid.getCellByField(key).name;
				widgets.push({
					type: type,
					name: key,
					label: label,
					required: required,
					staticValues: staticValues,
					datePattern: datePattern,
					validate: function() {
						var action = null;
						if (form) {
							var actionWidget = form.getWidget('action');
							action = actionWidget.get('value');
						}
						if (action == 'ignore') {
							return true;
						} else {
							return this.inherited('validate', arguments);
						}
					},
					value: value
				});
			}));
			form = new Form({
				widgets: widgets
			});
			if (focusWidget) {
				on.once(form, 'show', function() {
					var widget = this.getWidget(focusWidget);
					if (widget) {
						if (focusWidget == 'birthday') {
							widget = widget._dateBox;
						}
						setTimeout(function() {
							if (widget.focusNode) {
								widget.focusNode.select();
							}
						}, 500);
					}
				});
			}
			dialog.confirmForm({
				title: _('Edit this line'),
				submit: _('Apply'),
				form: form
			}).then(lang.hitch(this, function(values) {
				item.setValues(values);
				var recheck = null;
				if (values.action != 'ignore') {
					var itemObj = item.toObject();
					recheck = tools.umcpCommand('schoolcsvimport/recheck', {file_id: this.fileID, user_attrs: [itemObj]}).then(function(data) {
						var recheckedItem = data.result[0];
						item._initialValues.warnings = recheckedItem.warnings;
						item._initialValues.errors = recheckedItem.errors;
					});
					this.standbyDuring(recheck);
				}
				when(recheck).then(lang.hitch(this, function() {
					this.checkThemAll(grid);
				}));
			}));
		},

		startup: function() {
			this.inherited(arguments);
			var page = this.getPage('spreadsheet');
			page._form = new Form({
				region: 'top',
				widgets: [{
					type: CheckBox,
					name: 'show_errors',
					label: _('Show only lines with issues'),
					onClick: function() {
						var checked = this.get('value');
						var query = null; // all rows
						if (checked) {
							query = {errorState: 'not-all-good'};
						}
						page._grid._grid.setQuery(query);
					}
				}]
			});
			page.addChild(page._form);
			style.set(page._form.getButton('submit').domNode, {display: 'none'});
		},

		getFooterButtons: function(pageName) {
			var buttonDefinitions = this.inherited(arguments);
			if (pageName == 'upload') {
				buttonDefinitions = array.filter(buttonDefinitions, function(buttonDefinition) { return buttonDefinition.name !== 'next'; } );
			}
			return buttonDefinitions;
		},

		canCancel: function(pageName) {
			return pageName !== 'finished';
		},

		hasPrevious: function(pageName) {
			return array.indexOf(['finished', 'general'], pageName) === -1;
		}
	});

	return declare("umc.modules.schoolcsvimport", [ Module ], {
		_keepAlive: null,
		_wizard: null,

		buildRendering: function() {
			// This module uploads the file once and stores it in "memory"
			// i.e. the module is quite stateful. So we need to keep it alive
			// to not forget the files while the user is changing the rows
			var timeout = 1000 * Math.min(tools.status('sessionTimeout') / 2, 30);
			this._keepAlive = new timing.Timer(timeout);
			this._keepAlive.onTick = function() {
				tools.umcpCommand('schoolcsvimport/ping', {}, false);
			};
			this._keepAlive.start();

			var progressBar = new ProgressBar({});
			this.inherited(arguments);
			var wizard = new UploadWizard({
				description: this.description,
				progressBar: progressBar
			});
			this.addChild(wizard);

			wizard.on('finished', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
			wizard.on('cancel', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
		},

		destroy: function() {
			this._keepAlive.stop();
			this.inherited(arguments);
		}
	});

});
