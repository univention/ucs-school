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
	"dojo/on",
	"dojo/topic",
	"umc/dialog",
	"umc/store",
	"umc/tools",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/Module",
	"umc/widgets/Wizard",
	"umc/widgets/StandbyMixin",
	"umc/widgets/ComboBox",
	"umc/widgets/CheckBox",
	"umc/widgets/Uploader",
	"umc/widgets/ProgressBar",
	"umc/widgets/Text",
	"umc/widgets/Grid",
	"umc/i18n!umc/modules/schoolimport"
], function(declare, lang, on, topic, dialog, store, tools, Page, Form, Module, Wizard, StandbyMixin, ComboBox, CheckBox, Uploader, ProgressBar, Text, Grid, _) {

	var ImportWizard = declare("umc.modules.schoolimport.ImportWizard", [Wizard], {
		postMixInProperties: function() {
			this.pages = this.getPages();
			this._progressBar = new ProgressBar();
			this.inherited(arguments);
		},

		getPages: function() {
			return [{
				name: 'start',
				headerText: _('Perform new import'),
				helpText: 'foobar',
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
					name: 'usertype',
					label: _('User type'),
					description: _('Select the user type.'),
					autoHide: true,
					required: true,
					dynamicValues: 'schoolimport/usertypes'

				}]
			},{
				name: 'select-file',
				headerText: _('Select import database.'),
				helpText: _('Select CSV file ... '),
				widgets: [{
					type: Uploader,
					name: 'file',
					label: _('Upload file'),
					labelPosition: 'right',
					command: 'schoolimport/upload-file',
				//	dynamicOptions: lang.hitch(this, 'getUploaderParams'),
					onUploadStarted: lang.hitch(this, function() {
						this._progressBar.reset();
						this.standby(true, this._progressBar);
					}),
					onUploaded: lang.hitch(this, 'startDryRun'),
					onError: lang.hitch(this, function() {
						this.standby(false);
					})
				}]
			},{
				name: 'dry-run-overview',
				headerText: _('Overview about the import changes'),
				helpText: _('The following changes will be applied to the domain when continuing the import.'),
				widgets: [{
					name: 'summary',
					type: Text,  // FIXME: grid?
					content: '- 30 Benutzerkonten modifiziert,<br> - 10 Benutzerkonten gelöscht<br> - 100 Benutzerkonten neu angelegt'  // FIXME: get summary
				}, {
					type: CheckBox,
					name: 'email-notification',
					label: _('Inform me via E-Mail after the import was performed.')
				}]
			},{
				name: 'import-started',
				headerText: _('The import was started successfully.'),
				helpText: _('The list shows all current running imports.... You can download ...')
			},{
				name: 'error',  // FIXME: implement
				headerText: _('error'),
				helpText: _('error')
			},/*{
				name: '',
				headerText: '',
				helpText: '',
				widgets: []
			}*/];
		},

		getUploaderParams: function() {
			return {
				usertype: this.getWidget('start', 'usertype').get('value'),
				school: this.getWidget('start', 'school').get('value')
			};
		},

		startDryRun: function(response) {
			tools.umcpProgressCommand(this._progressBar, 'schoolimport/dry-run/start', lang.mixin(lang.clone(response.result), this.getUploaderParams())).then(lang.hitch(this, function() {
				this.standby(false);
				this._next('select-file');
			}), lang.hitch(this, function() {
				this.standby(false);
				// FIXME: show error page
			}));
		},

		next: function(pageName) {
			var nextPage = this.inherited(arguments);
			if (pageName === 'import-started') {
				nextPage = 'start';
			}
			if (nextPage === 'import-started') {
				return this.standbyDuring(this.umcpCommand('schoolimport/import/start')).then(lang.hitch(this, function() {
					this.buildImportsGrid(this.getPage(nextPage));
					return nextPage;
				}), lang.hitch(this, function() {
					return 'error';
				}));
			}
			return nextPage;
		},

		canFinish: function() {
			return true;
		},

		buildImportsGrid: function(parentWidget) {
			if (parentWidget._grid) {
				parentWidget.removeChild(parentWidget._grid);
				parentWidget._grid.destroyRecursive();
			}

			var grid = new Grid({
				moduleStore: store('id', 'schoolimport/jobs', this.moduleFlavor),
				columns: [{
					name: 'school',
					label: _('School')
				}, {
					name: 'creator',
					label: _('Creator')
				}, {
					name: 'user_type',
					label: _('User type')
				}, {
					name: 'date',
					label: _('Started at')
				}, {
					name: 'status',
					label: _('Status')
				}],
				actions: [{
					name: 'download-summary',
					label: _('Download summary'),
					description: _('......'),
					isStandardAction: true,
					isMultiAction: false,
					callback: function() {},
					canExecute: function(item) { return item.status === 'Finished'; }
				},{
					name: 'download-passwords',
					label: _('Download passwords'),
					description: _('......'),
					isStandardAction: true,
					isMultiAction: false,
					callback: function() {},
					canExecute: function(item) { return item.status === 'Finished'; }
				}, {
					name: 'download-logfile',
					label: _('Download logfiles'),
					description: _('......'),
					isStandardAction: true,
					isMultiAction: false,
					callback: function() {},
					canExecute: function(item) { return item.status === 'Finished'; }
				}]
			});

			grid.filter({query: ''});

			parentWidget.addChild(grid);
			parentWidget._grid = grid;
		},

		ready: function() {
			// FIXME: https://forge.univention.org/bugzilla/show_bug.cgi?id=45061
			return this.getPage('start')._form.ready();
		}
	});

	return declare("umc.modules.schoolimport", [Module], {
		unique: true,

		postMixInProperties: function() {
			this.inherited(arguments);
			this._wizard = new ImportWizard({ 'class': 'umcCard' });
		},

		buildRendering: function() {
			this.inherited(arguments);

			this.addChild(this._wizard);

			this.standbyDuring(this._wizard.ready());

			this._wizard.on('finished', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
			this._wizard.on('cancel', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
		}
	});
});
