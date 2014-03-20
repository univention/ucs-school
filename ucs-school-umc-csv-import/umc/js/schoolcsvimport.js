/*
 * Copyright 2014 Univention GmbH
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
	"dojo/Deferred",
	"dojo/store/Observable",
	"dojo/data/ItemFileWriteStore",
	"dojo/store/DataStore",
	"dojo/_base/window",
	"dojo/dom-construct",
	"dojo/dom-attr",
	"dojo/dom-geometry",
	"dojo/dom-style",
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
	"umc/widgets/Tooltip",
	"umc/modules/schoolcsvimport/DateBox",
	"umc/modules/schoolcsvimport/Grid",
	"umc/widgets/Module",
	"umc/i18n!umc/modules/schoolcsvimport"
], function(declare, lang, array, query, topic, when, Deferred, Observable, ItemFileWriteStore, DataStore, win, construct, attr, geometry, style, dateLocaleModule, Menu, CheckedMenuItem, timing, tools, dialog, Text, TextBox, Form, ProgressBar, ComboBox, Uploader, CheckBox, Wizard, Tooltip, DateBox, Grid, Module, _) {
	var UploadWizard = declare('umc.modules.schoolcsvimport.Wizard', Wizard, {
		postMixInProperties: function() {
			this.inherited(arguments);
			this.pages = [{
				name: 'general',
				headerText: this.description,
				helpText: _('This assistant guides through the individual steps for importing UCS@school users with a CSV file. At first, the user role for the users from the CSV file nneds to be specified.'),
				widgets: [{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					dynamicValues: 'schoolcsvimport/schools',
					autoHide: true
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
				}],
				layout: [['school'], ['type']]
			}, {
				name: 'upload',
				headerText: this.description,
				helpText: _('Please upload the CSV file. The CSV file has to contain comma separated values, enclosed by double quotes.'),
				widgets: [{
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
				}, {
					type: Text,
					name: 'csv_help',
					content: _('A "header" helps in the next step after uploading but it is not required.') + ' ' + _('Example of a file:') +
						'<pre>' +
							lang.replace('{username},{firstname},{lastname},{birthday}', {
								username: _('Username'),
								firstname: _('First name'),
								lastname: _('Last name'),
								birthday: _('Birthday')}) + '\n' +
							lang.replace('{example_username},{example_firstname},{example_lastname},{example_birthday}', {
								example_username: _('example_username'),
								example_firstname: _('example_firstname'),
								example_lastname: _('example_lastname'),
								example_birthday: _('example_birthday')}) + '\n' +
							'[...]' +
						'</pre>'
				}]
			}, {
				name: 'assign',
				headerText: this.description,
				helpText: _('The first lines of the CSV file are presented. It is necessary for the import to assign the individual columns concrete data types (first name, last name, ...). Please click on the header line of the table and choose the corresponding data type for each column. At least first name and last name need to be given.')
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
					content: _('No errors occurred during import.')
				}]
			}];
		},

		next: function(pageName) {
			var nextPage = this.inherited(arguments);
			var page = this.getPage(pageName);
			var deferred = new Deferred();
			var grid;
			if (pageName == 'assign') {
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
				if (array.indexOf(fields, 'username') == -1) {
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
					return this.standbyDuring(tools.umcpCommand('schoolcsvimport/show', {file_id: this.fileID, columns: fields}).then(lang.hitch(this, function(data) {
						var result = data.result;
						var page = this.getPage('spreadsheet');
						this.datePattern = result.date_pattern;
						page._grid = this.addGridSpreadSheet(page, result.columns, result.users);
						return nextPage;
					})));
				}));
			} else if (pageName == 'spreadsheet') {
				grid = page._grid;
				var items = grid.getAllItems();
				var userObjs = [];
				var nAdd = 0, nMod = 0, nDel = 0, nSkip = 0;
				var unresolvedErrors = false;
				array.forEach(items, function(item) {
					var action = item.action[0];
					if (action == 'create') {
						nAdd += 1;
					} else if (action == 'modify') {
						nMod += 1;
					} else if (action == 'delete') {
						nDel += 1;
					} else {
						nSkip += 1;
					}
					if (action != 'skip') {
						if (!tools.isEqual(item.errors[0], {})) {
							unresolvedErrors = true;
						}
						userObjs.push(item._toObject[0]());
					}
				});
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
						_('%s user(s) will be skipped', nSkip) +
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
							var importing = tools.umcpCommand('schoolcsvimport/import', {file_id: this.fileID, user_attrs: userObjs}).then(lang.hitch(this, function(data) {
								var errors = data.result;
								if (errors.length) {
									var widget = this.getWidget('finished', 'errors');
									var errorMessage = _('%d error(s) occurred:', errors.length);
									errorMessage = errorMessage + '<ul><li>' + errors.join('</li><li>') + '</li></ul>';
									widget.set('content', errorMessage);
								}
								deferred.resolve(nextPage);
							}), function() {
								deferred.reject();
							});
							this.standbyDuring(importing);
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
			return {school: school, type: type};
		},

		addMenuItem: function(headerMenu, label, name) {
			var updateGridField = lang.hitch(this, 'updateGridField');
			headerMenu.addChild(new CheckedMenuItem({
				label: label,
				name: name,
				onClick: function() {
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
			var dataStore = new ItemFileWriteStore({data: {
				label: 'line',
				items: users
			}});
			var objStore = new DataStore({ store: dataStore });
			var grid = new Grid({
				region: 'center',
				moduleStore: objStore,
				columns: givenColumns,
				footerFormatter: function() { return ''; },
				_updateContextItem: function() {},
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
			array.forEach(columns, lang.hitch(this, function(column) {
				var attributes = [column.label].concat(array.map(users, function(user) { return user[column.name]; }));
				column.width = this._getWidth(attributes) + 'px';
				column.noresize = true;
				column.defaultValue = '';
				if (column.name == 'action') {
					column.formatter = function(value) {
						var actionMap = {
							'delete' : _('Delete'),
							'create' : _('New'),
							'modify' : _('Change'),
							'skip' : _('Skip')
						};
						return actionMap[value];
					};
				}
			}));
			array.forEach(users, function(user) {
				user._initialValues = lang.clone(user);
				user._restore = lang.hitch(user, function() {
					this._setValues[0](this._initialValues[0]);
				});
				user._toObject = lang.hitch(user, function() {
					var obj = {};
					tools.forIn(this._initialValues[0], lang.hitch(this, function(k) {
						if (k in this) {
							obj[k] = this[k][0];
						}
					}));
					return obj;
				});
				user._setValues = lang.hitch(user, function(values) {
					tools.forIn(values, lang.hitch(this, function(k, v) {
						this[k] = [v];
					}));
				});
				user._resetError = lang.hitch(user, function() {
					this.errors = [{}];
					this.warnings = [{}];
					this.errorState = ['all-good'];
					if (this.action[0] == 'skip') {
						return;
					}
					tools.forIn(this._initialValues[0].errors, lang.hitch(this, function(field, notes) {
						array.forEach(notes, lang.hitch(this, function(note) {
							this._setError[0](field, note);
						}));
					}));
					tools.forIn(this._initialValues[0].warnings, lang.hitch(this, function(field, notes) {
						array.forEach(notes, lang.hitch(this, function(note) {
							this._setWarning[0](field, note);
						}));
					}));
				});
				user._setWarning = lang.hitch(user, function(field, note) {
					var warnings = this.warnings[0][field];
					if (!warnings) {
						warnings = this.warnings[0][field] = [];
					}
					warnings.push(note);
					this.errorState = ['not-all-good'];
				});
				user._setError = lang.hitch(user, function(field, note) {
					var errors = this.errors[0][field];
					if (!errors) {
						errors = this.errors[0][field] = [];
					}
					errors.push(note);
					this.errorState = ['not-all-good'];
				});
				user._styleError = lang.hitch(user, function(grid, row) {
					var hasIssues = false;
					tools.forIn(this.warnings[0], function(field) {
						hasIssues = true;
						row.customStyles += 'background-color: #FFFFE0;'; // lightyellow
						var cellIndex;
						array.forEach(grid.get('structure'), function(struct, i) {
							if (struct.field == field) {
								cellIndex = i + 1;
							}
						});
						var cellNode = query('.dojoxGridCell[idx$=' + cellIndex +']', row.node)[0];
						style.set(cellNode, {
							backgroundColor: '#FFFF00' // yellow
						});
					});
					tools.forIn(this.errors[0], function(field) {
						hasIssues = true;
						row.customStyles += 'background-color: #F08080;'; // lightcoral
						var cellIndex;
						array.forEach(grid.get('structure'), function(struct, i) {
							if (struct.field == field) {
								cellIndex = i + 1;
							}
						});
						var cellNode = query('.dojoxGridCell[idx$=' + cellIndex +']', row.node)[0];
						style.set(cellNode, {
							backgroundColor: '#FF0000', // red
							color: '#FFFFFF' // white, because of contrast
						});
					});
					if (hasIssues) {
						var completeErrorMessage = _('The following issues arose while checking this row:');
						completeErrorMessage += '<ul style="margin-left: -2em;">';
						array.forEach(grid.get('structure'), lang.hitch(this, function(struct) {
							var field = struct.field;
							var label = grid.getCellByField(field).name;
							var issues = lang.clone(this.errors[0][field] || []);
							issues = issues.concat(this.warnings[0][field] || []);
							if (issues.length) {
								completeErrorMessage += '<li>' + label + '<ul style="margin-left: -2em;">';
								array.forEach(issues, function(issue) {
									completeErrorMessage += '<li>' + issue + '</li>';
								});
								completeErrorMessage += '</ul></li>';
							}
						}));
						completeErrorMessage += '</ul>';
						var tooltip = new Tooltip({
							label: completeErrorMessage,
							connectId: [row.node]
						});
						grid.own(tooltip);
					}
				});
			});
			var dataStore = new ItemFileWriteStore({
				data: {
					label: 'username',
					items: users
				},
				hierarchical: false
			});
			var objStore = Observable(new DataStore({ store: dataStore }));
			var grid = new Grid({
				region: 'center',
				moduleStore: objStore,
				actions: [{
					name: 'reset',
					label: _('Reset'),
					description: _('Restore initial values from the uploaded file'),
					isMultiAction: true,
					isStandardAction: true,
					isContextAction: true,
					callback: lang.hitch(this, function(ids, items) {
						var itemObjs = [];
						array.forEach(items, function(item) {
							item._restore[0]();
							itemObjs.push(item._toObject[0]());
						});
						var recheck = tools.umcpCommand('schoolcsvimport/recheck', {file_id: this.fileID, user_attrs: itemObjs}).then(lang.hitch(this, function(data) {
							array.forEach(data.result, function(recheckedItem, i) {
								var item = items[i];
								item._initialValues[0].warnings = recheckedItem.warnings;
								item._initialValues[0].errors = recheckedItem.errors;
							});
							this.checkThemAll(grid);
						}));
						this.standbyDuring(recheck);
					})
				}, {
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
				}],
				columns: columns
			});
			//grid._grid.on('ApplyCellEdit', lang.hitch(this, function() {
			//	this.checkThemAll(grid);
			//}));
			grid._grid.on('StyleRow', function(row) {
				var item = this.getItem(row.index);
				if (item) {
					item._styleError[0](this, row);
				}
			});
			this.checkThemAll(grid);
			var lineIdx = grid._grid.getCellByField('line').index + 1;
			grid._grid.setSortIndex(lineIdx);
			parentWidget.addChild(grid);
			query('.dojoxGridScrollbox', grid.domNode).style('overflowX', 'auto');
			return grid;
		},

		checkThemAll: function(grid) {
			var items = grid.getAllItems();
			var usernames = [];
			var doubles = [];
			var dateConstraints = {datePattern: this.datePattern, selector: 'date'};
			array.forEach(items, function(item) {
				item._resetError[0]();
				if (item.action[0] == 'skip') {
					return;
				}
				var birthday = item.birthday[0];
				if (birthday) {
					var parsedDate = dateLocaleModule.parse(birthday, dateConstraints);
					if (!parsedDate) {
						item._setError[0]('birthday', _('The birthday does not follow the format for dates. Please change the birthday.'), grid._grid);
					}
				}
				var username = item.username[0];
				if (array.indexOf(doubles, username) !== -1) {
					return;
				}
				if (array.indexOf(usernames, username) !== -1) {
					doubles.push(username);
					return;
				}
				usernames.push(username);
			});
			array.forEach(doubles, function(username) {
				array.forEach(items, function(item) {
					if (item.username[0] == username) {
						item._setError[0]('username', _('Username occurs multiple times in the file. Please change the usernames so that all are unique.'), grid._grid);
					}
				});
			});
			grid._grid.update();
		},

		openEditDialog: function(item, grid) {
			var widgets = [];
			array.forEach(grid._grid.get('structure'), lang.hitch(this, function(struct) {
				var key = struct.field;
				var value = item[key][0];
				if (key == 'line') {
					return;
				}
				var type = TextBox;
				var staticValues = null;
				var datePattern = null;
				var required = array.indexOf(['action', 'firstname', 'lastname', 'username'], key) !== -1;
				if (key == 'birthday') {
					type = DateBox;
					datePattern = this.datePattern;
				}
				if (key == 'action') {
					type = ComboBox;
					staticValues = [{id: 'create', label: _('New')}, {id: 'modify', label: _('Change')}, {id: 'delete', label: _('Delete')}, {id: 'skip', label: _('Skip')}];
				}
				var label = grid._grid.getCellByField(key).name;
				widgets.push({
					type: type,
					name: key,
					label: label,
					required: required,
					staticValues: staticValues,
					datePattern: datePattern,
					value: value
				});
			}));
			dialog.confirmForm({
				title: _('Edit this line'),
				submit: _('Edit'),
				widgets: widgets
			}).then(lang.hitch(this, function(values) {
				item._setValues[0](values);
				var recheck = null;
				if (values.action != 'skip') {
					var itemObj = item._toObject[0]();
					recheck = tools.umcpCommand('schoolcsvimport/recheck', {file_id: this.fileID, user_attrs: [itemObj]}).then(function(data) {
						var recheckedItem = data.result[0];
						item._initialValues[0].warnings = recheckedItem.warnings;
						item._initialValues[0].errors = recheckedItem.errors;
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
					onClick: lang.hitch(this, function() {
						var page = this.getPage('spreadsheet');
						var checked = page._form.get('value').show_errors;
						var query = null; // all rows
						if (checked) {
							query = {errorState: 'not-all-good'};
						}
						page._grid._grid.setQuery(query);
					})
				}]
			});
			page.addChild(page._form);
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
			return pageName !== 'finished';
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
