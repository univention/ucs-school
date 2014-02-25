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
	"dojo/Deferred",
	"dojo/store/Memory",
	"dojo/store/Observable",
	"dojo/data/ItemFileWriteStore",
	"dojo/store/DataStore",
	"dojo/_base/window",
	"dojo/dom-construct",
	"dojo/dom-attr",
	"dojo/dom-geometry",
	"dojo/dom-style",
	"dijit/Menu",
	"dijit/CheckedMenuItem",
	"dojox/grid/cells",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Text",
	"umc/widgets/TextBox",
	"umc/widgets/DateBox",
	"umc/widgets/Form",
	"umc/widgets/ProgressBar",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/ComboBox",
	"umc/widgets/Uploader",
	"umc/widgets/CheckBox",
	"umc/widgets/Wizard",
	"umc/widgets/Tooltip",
	"umc/modules/schoolcsvimport/Grid",
	"umc/widgets/Module",
	"umc/i18n!umc/modules/schoolcsvimport"
], function(declare, lang, array, query, topic, Deferred, Memory, Observable, ItemFileWriteStore, DataStore, win, construct, attr, geometry, style, Menu, CheckedMenuItem, dojoxGridCells, tools, dialog, Text, TextBox, DateBox, Form, ProgressBar, ExpandingTitlePane, ComboBox, Uploader, CheckBox, Wizard, Tooltip, Grid, Module, _) {
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
					onUploaded: lang.hitch(this, function(result) {
						this._next('upload');
					})
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

		errorsWhileSaving: function(errors) {
			if (errors.length) {
				var widget = this.getWidget('finished', 'errors');
				var errorMessage = _('%d error(s) occurred:', errors.length);
				errorMessage = errorMessage + '<ul><li>' + errors.join('</li><li>') + '</li></ul>';
				widget.set('content', errorMessage);
			}
		},

		updateProgress: function(progresses, deferred, nextPage, handleErrors) {
			if (progresses) {
				var nextProgress = progresses.shift();
				if (nextProgress) {
					if (nextProgress.errors && handleErrors) {
						var nextPageWidget = this.getPage(nextPage);
						if (nextPageWidget._hadErrors) {
							delete nextProgress.errors;
						} else {
							nextPageWidget._hadErrors = true;
						}
					}
					deferred.progress(nextProgress);
					if (nextProgress.errors && handleErrors) {
						setTimeout(function() { deferred.reject(nextPage); }, 1400);
					} else {
						setTimeout(lang.hitch(this, function() { this.updateProgress(progresses, deferred, nextPage, handleErrors); }), 700);
					}
				} else {
					deferred.resolve(nextPage);
				}
			}
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
				if (fields.indexOf('firstname') == -1 || fields.indexOf('lastname') == -1) {
					dialog.alert(_('You need to specify at least "%(firstname)s" and "%(lastname)s" as columns. Click on the column header in the table', {firstname: _('First name'), lastname: _('Last name')}));
					deferred.reject();
					return deferred;
				}
				var auto_username = false;
				if (fields.indexOf('username') == -1) {
					auto_username = true;
				}
				var args = {
					fields: fields,
					auto_username: auto_username
				};
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
			} else if (pageName == 'spreadsheet') {
				grid = page._grid;
				var items = grid.getAllItems();
				var nAdd = 0, nMod = 0, nDel = 0;
				var unresolvedErrors = false;
				array.forEach(items, function(item) {
					if (item.errorState[0] == 'not-all-good') {
						unresolvedErrors = true;
					}
					var action = item.action[0];
					if (action == 'create') {
						nAdd += 1;
					} else if (action == 'modify') {
						nMod += 1;
					} else {
						nDel += 1;
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
					'</li></ul>', [{
					label: _('Cancel'),
					name: 'cancel'
				}, {
					label: _('Confirm changes'),
					name: 'continue',
					'default': true
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
			// return deferred;
			return deferred.then(lang.hitch(this, function() {
				var allProgresses = {
					upload: [{
						component: 'Loading users',
						percentage: 20
					}, {
						//errors: ['File needs to be to in the CSV format. Try again'],
						percentage: 90
					}],
					assign: [{
						component: 'Loading users',
						percentage: 30
					}, {
						percentage: 60
					}, {
						percentage: 90
					}],
					spreadsheet: [{
						component: 'Importing users',
						message: 'Importing max.mustermann',
						percentage: 50
					}, {
						message: 'Importing susanne.bauer',
						errors: ['susanne.bauer could not be saved: Already exists in another school'],
						percentage: 100
					}]
				};
				var progresses = allProgresses[pageName];
				this.progressBar.reset();
				if (progresses) {
					var progressDeferred = new Deferred();
					this.progressBar.feedFromDeferred(progressDeferred);
					var handleErrors = true;
					var cb = lang.hitch(this.progressBar, 'stop', function(){}, undefined, true);
					if (pageName == 'spreadsheet') {
						handleErrors = false;
						cb = lang.hitch(this, function() {
							this.errorsWhileSaving(this.progressBar.getErrors().errors);
						});
					}
					this.updateProgress(progresses, progressDeferred, nextPage, handleErrors);
					progressDeferred.then(undefined, cb);
					this.standbyDuring(progressDeferred, this.progressBar);
					return progressDeferred;
				} else {
					return nextPage;
				}
			}));
		},

		addMenuItem: function(headerMenu, label, name) {
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
					var columnNode;
					array.forEach(grid.get('structure'), function(struct) {
						columnNode = grid.getCellByField(struct.field);
						if (columnNode.field == myField) {
							columnNode._usedAs = fieldName;
							columnNode.name = fieldLabel;
						} else if (columnNode.name == fieldLabel) {
							delete columnNode._usedAs;
							columnNode.name = unusedLabel;
						}
					});
					grid.update();
				}
			}));
		},

		addGridAssign: function(parentWidget, columns, users) {
			var headerMenu = new Menu({
				leftClickToOpen: true
			});
			this.own(headerMenu);
			this.addMenuItem(headerMenu, _('Unused'), 'unused');
			this.addMenuItem(headerMenu, _('Username'), 'username');
			this.addMenuItem(headerMenu, _('First name'), 'firstname');
			this.addMenuItem(headerMenu, _('Last name'), 'lastname');
			this.addMenuItem(headerMenu, _('Birthday'), 'birthday');
			this.addMenuItem(headerMenu, _('Class'), 'class');
			this.addMenuItem(headerMenu, _('Email'), 'email');
			var dataStore = new ItemFileWriteStore({data: {
				label: 'line',
				items: users
			}});
			var objStore = new DataStore({ store: dataStore });
			var grid = new Grid({
				region: 'center',
				moduleStore: objStore,
				columns: columns,
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
			}));
			array.forEach(users, function(user) {
				user._initialValues = lang.clone(user);
				user._restore = lang.hitch(user, function() {
					this._setValues[0](this._initialValues[0]);
				});
				user._setValues = lang.hitch(user, function(values) {
					tools.forIn(values, lang.hitch(this, function(k, v) {
						this[k] = [v];
					}));
				});
				user._resetError = lang.hitch(user, function() {
					this.errors = [{}];
					this.errorState = ['all-good'];
				});
				user._setError = lang.hitch(user, function(field, note) {
					this.errors[0][field] = note;
					this.errorState = ['not-all-good'];
				});
				user._styleError = lang.hitch(user, function(grid, row) {
					tools.forIn(this.errors[0], function(field, note) {
						row.customStyles += 'background-color: #F08080;'; // lightcoral
						var cellIndex;
						array.forEach(grid.get('structure'), function(struct, i) {
							if (struct.field == field) {
								cellIndex = i + 1;
							}
						});
						var cellNode = query('.dojoxGridCell[idx$=' + cellIndex +']', row.node)[0];
						style.set(cellNode, {backgroundColor: '#FF0000'}); // red
						var tooltip = new Tooltip({
							label: note,
							connectId: [cellNode]
						});
						grid.own(tooltip);
					});
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
						array.forEach(items, function(item) {
							item._restore[0]();
						});
						this.checkThemAll(grid);
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
			array.forEach(items, function(item) {
				item._resetError[0]();
				var username = item.username[0];
				if (doubles.indexOf(username) !== -1) {
					return;
				}
				if (usernames.indexOf(username) !== -1) {
					doubles.push(username);
					return;
				}
				usernames.push(username);
			});
			array.forEach(doubles, function(username) {
				array.forEach(items, function(item) {
					if (item.username[0] == username) {
						item._setError[0]('username', _('Username is not unique'), grid._grid);
					}
				});
			});
			grid._grid.update();
		},

		openEditDialog: function(item, grid) {
			var widgets = [];
			tools.forIn(item._initialValues[0], function(key) {
				value = item[key][0];
				if (key == 'line') {
					return;
				}
				var type = TextBox;
				var staticValues = null;
				var required = ['action', 'firstname', 'lastname', 'username'].indexOf(key) !== -1;
				if (key == 'birthday') {
					type = DateBox;
					var match = value.match('(\\d{2}).(\\d{2}).(\\d{4})');
					if (match) {
						value = match.slice(1).reverse().join('-');
					}
				}
				if (key == 'action') {
					type = ComboBox;
					staticValues = [{id: 'create', label: 'create'}, {id: 'modify', label: 'modify'}, {id: 'delete', label: 'delete'}];
				}
				var label = grid._grid.getCellByField(key).name;
				widgets.push({
					type: type,
					name: key,
					label: label,
					required: required,
					staticValues: staticValues,
					value: value
				});
			});
			dialog.confirmForm({
				title: _('Edit this line'),
				submit: _('Edit'),
				widgets: widgets
			}).then(lang.hitch(this, function(values) {
				if (values.birthday) {
					var match = values.birthday.match('(\\d{4})-(\\d{2}).(\\d{2})');
					if (match) {
						values.birthday = match.slice(1).reverse().join('.');
					}
				}
				item._setValues[0](values);
				grid._grid.update();
				this.checkThemAll(grid);
			}));
		},

		startup: function() {
			this.inherited(arguments);
			var columns;
			var users;
			columns = [{
				name: 'unused1',
				label: _('Unused')
			}, {
				name: 'unused2',
				label: _('Unused')
			}, {
				name: 'unused3',
				label: _('Unused')
			}, {
				name: 'unused4',
				label: _('Unused')
			}];
			users = [{
				line: 1,
				unused1: 'Max',
				unused2: 'Mustermann',
				unused3: '02.05.2002',
				unused4: '5a'
			}, {
				line: 2,
				unused1: 'Susanne',
				unused2: 'Bauer',
				unused3: '12.07.2004',
				unused4: '3b'
			}];
			var page = this.getPage('assign');
			page._grid = this.addGridAssign(page, columns, users);

			page = this.getPage('spreadsheet');
			columns = [{
				name: 'action',
				label: _('Action')
			}, {
				name: 'username',
				label: _('Username')
			}, {
				name: 'firstname',
				label: _('First name')
			}, {
				name: 'lastname',
				label: _('Last name')
			}, {
				defaultValue: '',
				name: 'birthday',
				label: _('Birthday')
			}, {
				defaultValue: '',
				name: 'class',
				label: _('Class')
			}, {
				defaultValue: '',
				name: 'email',
				label: _('Email')
			}, {
				name: 'line',
				defaultValue: '',
				label: _('Line')
			}];
			users = [{
				line: 1,
				action: 'create',
				username: 'max.mustermann',
				firstname: 'Max',
				lastname: 'Mustermann',
				birthday: '02.05.2002',
				'class': '5a'
			}, {
				line: 2,
				action: 'modify',
				username: 'susanne.bauer',
				firstname: 'Susanne',
				lastname: 'Bauer',
				birthday: '12.07.2004',
				'class': '3b',
				email: 'susanne.bauer@grundschule.bremen.de'
			}, {
				line: 3,
				action: 'modify',
				username: 'thomas.klein',
				firstname: 'Thomas Stefan',
				lastname: 'Klein',
				birthday: '01.02.2002',
				'class': '5a',
				email: 'thommy@grundschule.bremen.de'
			}, {
				line: 4,
				action: 'create',
				username: 'susanne.bauer',
				firstname: 'Susanne',
				lastname: 'Bauer',
				birthday: '09.10.2007',
				'class': '1c'
			}, {
				action: 'delete',
				username: 'maria.kuhne',
				firstname: 'Maria Sophie',
				lastname: 'Kuhne',
				birthday: '20.12.2001',
				'class': '6a',
				email: 'mariechen@grundschule.bremen.de'
			}];
			page._form = new Form({
				region: 'top',
				widgets: [{
					type: CheckBox,
					name: 'show_errors',
					label: _('Show only lines with errors'),
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
			page._grid = this.addGridSpreadSheet(page, columns, users);
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
		_wizard: null,

		buildRendering: function() {
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
		}
	});

});
