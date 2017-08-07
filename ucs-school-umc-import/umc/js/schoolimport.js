/*
 * Copyright 2017 Univention GmbH
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
	"dojo/on",
	"dojo/topic",
	"dojo/promise/all",
	"dojo/Deferred",
	"dojox/html/entities",
	"umc/dialog",
	"umc/store",
	"umc/tools",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/Module",
	"umc/widgets/Wizard",
	"umc/widgets/StandbyMixin",
	"umc/widgets/ComboBox",
	"umc/widgets/Uploader",
	"umc/widgets/ProgressBar",
	"umc/widgets/Text",
	"umc/widgets/Grid",
	"umc/widgets/HiddenInput",
	"umc/i18n!umc/modules/schoolimport"
], function(declare, lang, array, on, topic, all, Deferred, entities, dialog, store, tools, Page, Form, Module, Wizard, StandbyMixin, ComboBox, Uploader, ProgressBar, Text, Grid, HiddenInput, _) {

	var ImportWizard = declare("umc.modules.schoolimport.ImportWizard", [Wizard], {

		autoValidate: true,

		postMixInProperties: function() {
			this.pages = this.getPages();
			this.initialQuery = new Deferred();
			this.initialQuery.then(lang.hitch(this, function() {
				if (!this.getPage('overview')._grid.getAllItems().length) {
					this._next('overview');
				}
			}));
			this._progressBar = new ProgressBar();
			this.inherited(arguments);
		},

		getPages: function() {
			return [{
				name: 'overview',
				headerText: _('Overview User Imports'),
				headerTextRegion: 'main',
				helpText: _('List of running and completed user imports. For every completed user import a summary is provided with every change that was made as well as a list of passwords for newly created user accounts.'),
				helpTextRegion: 'main'
			},{
				name: 'start',
				headerText: _('Import user accounts'),
				helpText: _('Please select the school and the role of user for the import.'),
				widgets: [{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					description: _('Select the school where the import should be done.'),
					autoHide: true,
					required: true,
					dynamicValues: 'schoolimport/schools'
				},{
					type: ComboBox,
					name: 'userrole',
					label: _('User role'),
					description: _('Select the user role.'),
					autoHide: true,
					required: true,
					dynamicValues: 'schoolimport/userroles'
				}]
			},{
				name: 'select-file',
				headerText: _('Upload data'),
				helpText: _('Please select and upload the data export from the School Information System.'),
				widgets: [{
					type: Uploader,
					name: 'file',
					label: _('Please select a file. This will start a validation proccess of the data.'),
					buttonLabel: _('Select file'),
					command: 'schoolimport/upload-file',
					onUploadStarted: lang.hitch(this, function() {
						this._progressBar.reset(_('Please wait until the examination of the data is complete.'));
						this.standby(true, this._progressBar);
					}),
					onUploaded: lang.hitch(this, 'startDryRun'),
					onError: lang.hitch(this, function() {
						this.standby(false);
					})
				}, {
					type: HiddenInput,
					name: 'filename',
				}]
			},{
				name: 'dry-run-overview',
				headerText: _('Data examination completed'),
				helpText: _('The examination of the uploaded data completed successfully. Following, you see the output of the data import interfrace. Press "Start Import" to proceed with the actual user import.'),
				widgets: [{
					name: 'summary',
					type: Text,
					content: ''
				}]
			},{
				name: 'import-started',
				headerText: _('The import was started successfully.'),
				helpTextRegion: 'main',
				helpTextAllowHTML: false,
			},{
				name: 'error',  // FIXME: implement
				headerText: _('An error occurred.'),
				helpText: _('Please notify the system administrator about this error via email.'),
				helpTextAllowHTML: true
			},/*{
				name: '',
				headerText: '',
				helpText: '',
				widgets: []
			}*/];
		},

		getUploaderParams: function() {
			return {
				userrole: this.getWidget('start', 'userrole').get('value'),
				school: this.getWidget('start', 'school').get('value'),
				filename: this.getWidget('select-file', 'filename').get('value') || undefined
			};
		},

		startDryRun: function(response) {
			this.getWidget('select-file', 'filename').set('value', response.result.filename);
			tools.umcpProgressCommand(this._progressBar, 'schoolimport/dry-run/start', this.getUploaderParams(), {display400: function() {}}).then(lang.hitch(this, function(result) {
				this.getWidget('dry-run-overview', 'summary').set('content', entities.encode(result.summary));
				this.standby(false);
				this._next('select-file');
			}), lang.hitch(this, function(error) {
				console.log(error);
				var msg = _('Please notify the system administrator about this error via email.');
				this.getPage('error').set('helpText', msg);
				this.standby(false);
				this.switchPage('error');
			}));
		},

		isPageVisible: function(pageName) {
			if (pageName === 'error') {
				return false;
			}
			return this.inherited(arguments);
		},

		next: function(pageName) {
			var nextPage = this.inherited(arguments);
			if (pageName === 'import-started') {
				nextPage = 'overview';
			}
			if (nextPage === 'import-started') {
				return this.standbyDuring(tools.umcpCommand('schoolimport/import/start', this.getUploaderParams())).then(lang.hitch(this, function(response) {
					this.getPage(nextPage).set('helpText', _('A new import of %(role)s users at school %(school)s has been started. The import has the ID %(id)s.', {'id': response.result.id, 'role': response.result.userrole, 'school': response.result.school}));
					return nextPage;
				}), lang.hitch(this, function() {
					return 'error';
				}));
			}
			if (nextPage === 'overview') {
				this.buildImportsGrid(this.getPage(nextPage));
			}
			return nextPage;
		},

		getFooterButtons: function(pageName) {
			var buttons = this.inherited(arguments);
			array.forEach(buttons, lang.hitch(this, function(button) {
				if (pageName === 'overview' && button.name === 'next') {
					button.label = _('Start a new import');
				}
				if (pageName === 'dry-run-overview' && button.name === 'next') {
					button.label = _('Start import');
				}
				if (pageName === 'import-started' && button.name === 'next') {
					button.label = _('View finished imports');
				}
			}));
			return array.filter(buttons, function(button) {
				if (pageName === 'error' && button.name === 'finish') {
					return false;
				}
				if (pageName === 'select-file' && button.name === 'finish') {
					return false;
				}
				return true;
			});
		},

		hasNext: function(pageName) {
			if (~array.indexOf(['select-file', 'error'], pageName)) {
				return false;
			}
			if (pageName === 'import-started') {
				return true;
			}
			return this.inherited(arguments);
		},

		hasPrevious: function(pageName) {
			if (~array.indexOf(['import-started', 'dry-run-overview', 'error'], pageName)) {
				return false;
			}
			return this.inherited(arguments);
		},

		canFinish: function(values, pageName) {
			if (pageName === 'error') {
				return true;
			}
			return false;  // the wizard is a loop which starts at the beginning
		},

		buildImportsGrid: function(parentWidget) {
			if (parentWidget._grid) {
				parentWidget.removeChild(parentWidget._grid);
				parentWidget._grid.destroyRecursive();
			}

			var grid = new Grid({
				gridOptions: { selectionMode: 'none' },
				moduleStore: store('id', 'schoolimport/jobs', this.moduleFlavor),
				actions: [{
					name: 'reload',
					label: _('Reload'),
					isContextAction: false,
					callback: function() { grid.filter({query: ''}); }
				}, {
					name: 'start',
					label: _('Start a new import'),
					isContextAction: false,
					callback: lang.hitch(this, function() {
						this._next('overview');
					})
				}],
				columns: [{
					name: 'id',
					label: _('Job Id')
				}, {
					name: 'date',
					label: _('Started at'),
					formatter: function(value) {
						return value; // FIXME:
					}
				}, {
					name: 'school',
					label: _('School')
				}, {
					name: 'creator',
					label: _('Started by')
				}, {
					name: 'userrole',
					label: _('User role')
				}, {
					name: 'status',
					label: _('Status')
				}, {
					name: 'download-passwords',
					label: _('Passwords'),
					formatter: function(value, item) {
						return new Text({
							content: _('<a href="/univention/command/schoolimport/job/passwords.csv?job=%s" target="_blank"><img style="height: 24px;" src="/univention/js/dijit/themes/umc/icons/scalable/schoolimport-passwords.svg"> Passwords</>', encodeURIComponent(item.id))
						});
					}
				}, {
					name: 'download-summary',
					label: _('Summary'),
					formatter: function(value, item) {
						return new Text({
							content: _('<a href="/univention/command/schoolimport/job/summary.csv?job=%s" target="_blank"><img style="height: 24px;" src="/univention/js/dijit/themes/umc/icons/scalable/schoolimport-download.svg"> Summary</>', encodeURIComponent(item.id))
						});
					}
				}]
			});

			grid.filter({query: ''});
			grid.on('filterDone', lang.hitch(this, function() {
				if (!this.initialQuery.isFulfilled()) {
					this.initialQuery.resolve();
				}
			}));

			parentWidget.addChild(grid);
			parentWidget._grid = grid;
		},

		ready: function() {
			// FIXME: https://forge.univention.org/bugzilla/show_bug.cgi?id=45061
			return all(array.map(array.filter(this._pages, function(page) { return page._form; }), function(page) {
				return page._form.ready();
			}));
		}
	});

	return declare("umc.modules.schoolimport", [Module], {
		unique: true,
		standbyOpacity: 1,

		postMixInProperties: function() {
			this.inherited(arguments);
			this._wizard = new ImportWizard({ 'class': 'umcCard' });
			this.standbyDuring(this._wizard.ready().then(lang.hitch(this, function() { return this._wizard.initialQuery; })));
		},

		buildRendering: function() {
			this.inherited(arguments);

			this.addChild(this._wizard);

			this._wizard.on('finished', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
			this._wizard.on('cancel', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
		}
	});
});
