/*
 * Copyright 2011-2015 Univention GmbH
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
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiUploader",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/DateBox",
	"umc/widgets/TimeBox",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/distribution"
], function(declare, lang, array, dialog, tools, Page, Form, TextBox, ComboBox, MultiUploader, MultiObjectSelect, DateBox, TimeBox, StandbyMixin, _) {

	return declare("umc.modules.distribution.DetailPage", [ Page, StandbyMixin ], {
		// summary:
		//		This class represents the detail view of our dummy module.

		// reference to the module's store object
		moduleStore: null,

		// reference to umcpCommand with the correct flavor
		umcpCommand: null,

		// currently active flavor of the module
		moduleFlavor: '',

		// internal reference to the formular containing all form widgets of an UDM object
		_form: null,

		postMixInProperties: function() {
			// is called after all inherited properties/methods have been mixed
			// into the object (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			// Set the opacity for the standby animation to 100% in order to mask
			// GUI changes when the module is opened. Call this.standby(true|false)
			// to enabled/disable the animation.
			this.standbyOpacity = 1;

			// set the page header
			this.headerText = _('Project properties');
			this.helpText = _('This page allows to modify properties of an existing or new distribution project.');

			// configure buttons for the footer of the detail page
			this.footerButtons = [{
				name: 'submit',
				label: _('Save changes'),
				callback: lang.hitch(this, function() {
					this._save(this._form.get('value'));
				})
			}, {
				name: 'cancel',
				label: _('Back to overview'),
				callback: lang.hitch(this, function() {
					this.onClose();
					this._resetForm();
				})
			}];
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);
			this.standby(true);

			// query max upload size via UCR
			tools.ucr('umc/server/upload/max').then(lang.hitch(this, function(result) {
				this.standby(false);
				var maxSize = result['umc/server/upload/max'] || 10240;
				this.renderDetailPage(maxSize);
			}), lang.hitch(this, function() {
				// some error occurred :/ ... take a default value
				this.standby(false);
				this.renderDetailPage(10240);
			}));
		},

		renderDetailPage: function(maxUploadSize) {
			// render the form containing all detail information that may be edited

			// specify all widgets
			var widgets = [{
				type: TextBox,
				name: 'description',
				label: _('Description'),
				description: _('The description of the teaching material project'),
				required: true
			}, {
				type: TextBox,
				name: 'name',
				label: _('Directory name'),
				description: _('The name of the project directory as it will be displayed in the file system.'),
				depends: 'description',
				required: true,
				dynamicValue: lang.hitch(this, function(values) {
					var me = this._form.getWidget('name');
					if (me.get('disabled')) {
						// widget is disabled, do not change the value
						return me.get('value');
					}

					// avoid certain characters for the filename
					var desc = values.description;
					array.forEach([/\//g, /\\/g, /\?/g, /%/g, /\*/g, /:/g, /\|/g, /"/g, /</g, />/g, /\$/g, /'/g], function(ichar) {
						desc = desc.replace(ichar, '_');
					});

					// limit the filename length
					return desc.slice(0, 255);
				})
			}, {
				type: MultiUploader,
				multiFile: true,
				name: 'files',
				command: 'distribution/upload',
				dynamicOptions: {
					flavor: this.moduleFlavor
				},
				showClearButton: false,
				label: _('Files'),
				labelPosition: 'top',
				description: _('Files that have been added to this teaching material project'),
				maxSize: maxUploadSize * 1024, // conversion from kbyte to byte
				canUpload: lang.hitch(this, '_checkFilenameUpload'),
				canRemove: lang.hitch(this, '_checkFilenamesRemove')
			}, {
				type: MultiObjectSelect,
				name: 'recipients',
				dialogTitle: _('Assign classes/workgroups'),
				label: _('Assigned classes/workgroups'),
				description: _('List of groups that are marked to receive the teaching materials'),
				queryWidgets: [{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					dynamicValues: 'distribution/schools',
					umcpCommand: lang.hitch(this, 'umcpCommand'),
					autoHide: true
				}, {
					type: TextBox,
					name: 'pattern',
					label: _('Search name')
				}],
				queryCommand: lang.hitch(this, function(options) {
					return this.umcpCommand('distribution/groups', options).then(function(data) {
						return data.result;
					});
				}),
				formatter: function(dnList) {
					var tmp = array.map(dnList, function(i) {
						return i;
					});
					return tmp;
				},
				autoSearch: true
			}, {
				type: ComboBox,
				name: 'distributeType',
				label: _('Distribution of project files'),
				description: _('Specifies whether the project data is distributed automatically or manually.'),
				value: 'manual',
				staticValues: [{
					id: 'manual',
					label: _('Manual distribution')
				}, {
					id: 'automatic',
					label: _('Automatic distribution')
				}]
			}, {
				type: DateBox,
				name: 'distributeDate',
				label: _('Distribution date'),
				description: _('Date at which the project files will be distributed automatically.'),
				visible: false
			}, {
				type: TimeBox,
				name: 'distributeTime',
				label: _('Distribution time'),
				description: _('Time at which the project files will be distributed automatically.'),
				visible: false
			}, {
				type: ComboBox,
				name: 'collectType',
				label: _('Collection of project files'),
				description: _('Specifies whether the project data is collected automatically or manually.'),
				value: 'manual',
				staticValues: [{
					id: 'manual',
					label: _('Manual collection')
				}, {
					id: 'automatic',
					label: _('Automatic collection')
				}]
			}, {
				type: DateBox,
				name: 'collectDate',
				label: _('Collection date'),
				description: _('Date at which the project files will be collected automatically.')
			}, {
				type: TimeBox,
				name: 'collectTime',
				label: _('Collection time'),
				description: _('Time at which the project files will be collected automatically.')
			}];

			// specify the layout... additional dicts are used to group form elements
			// together into title panes
			var layout = [{
				label: _('General'),
				layout: [ [ 'description', 'name' ] ]
			}, {
				label: _('Distribution and collection of project files'),
				layout: [
					'distributeType', [ 'distributeDate', 'distributeTime' ],
					'collectType', [ 'collectDate', 'collectTime' ]
				]
			}, {
				label: _('Members'),
				layout: [ 'recipients' ]
			}, {
				label: _('Files'),
				layout: [ 'files' ]
			}];

			// create the form
			this._form = new Form({
				widgets: widgets,
				layout: layout,
				moduleStore: this.moduleStore,
				scrollable: true
			});

			// add form to page... the page extends a BorderContainer, by default
			// an element gets added to the center region
			this.addChild(this._form);

			// hook to onSubmit event of the form
			this._form.on('submit', lang.hitch(this, '_save'));

			// manage visible/hidden elements
			this.own(this._form.getWidget('distributeType').watch('value', lang.hitch(this, function(name, old, value) {
				this._form.getWidget('distributeDate').set('visible', value != 'manual');
				this._form.getWidget('distributeTime').set('visible', value != 'manual');
			})));
			this.own(this._form.getWidget('collectType').watch('value', lang.hitch(this, function(name, old, value) {
				this._form.getWidget('collectDate').set('visible', value != 'manual');
				this._form.getWidget('collectTime').set('visible', value != 'manual');
			})));
		},

		_checkFilenamesRemove: function(filenames) {
			var nameWidget = this._form.getWidget('name');
			var isNewProject = !nameWidget.get('disabled');
			return this.umcpCommand('distribution/checkfiles', {
				project: isNewProject ? null : nameWidget.get('value'),
				filenames: filenames
			}).then(lang.hitch(this, function(response) {
				// do allow removal if any file has already been distributed
				var results = response.result;
				var distributedFiles = [];
				array.forEach(results, function(i) {
					if (i.distributed) {
						distributedFiles.unshift(i.filename);
					}
				});
				if (distributedFiles.length > 0) {
					dialog.alert(_('The following files cannot be removed as they have already been distributed: %s', '<ul><li>' + distributedFiles.join('</li><li>') + '</li></ul>'));
					return false;
				}

				// everything OK :)
				return true;
			}));
		},

		_checkFilenameUpload: function(fileInfo) {
			var filenames;
			if ('name' in fileInfo){
				filenames = [ fileInfo.name ];
			}else{
				if (fileInfo.length > 1) {
					filenames = [];
					fileInfo.forEach(function(ifile){
						filenames.push(ifile.name);
					});
				}
			}
			var nameWidget = this._form.getWidget('name');
			var isNewProject = !nameWidget.get('disabled');

			return this.umcpCommand('distribution/checkfiles', {
				project: isNewProject ? null : nameWidget.get('value'),
				filenames: filenames
			}).then(function(response) {

				var distributed = [];
				var projectDuplicate = [];
				var sessionDuplicate = [];
				var result = response.result;

				array.forEach(result, lang.hitch(this, function(ifile){
					if (ifile.distributed){
						distributed.push(ifile.filename);
					}
					if (ifile.projectDuplicate){
						projectDuplicate.push(ifile.filename);
					}
					if (ifile.sessionDuplicate){
						sessionDuplicate.push(ifile.filename);
					}
				}));

				if (distributed.length > 0){
					// do not allow the upload of an already distributed file
					var files = distributed.join();
					dialog.alert(_('The following files cannot be uploaded as they have already been distributed: %s','<ul><li>' + distributed.join('</li><li>') + '</li></ul>'));
					return false;
				}

				if (projectDuplicate.length > 0){
					// a file exists in the project, but has not been distributed yet
					return dialog.confirm(_('The following files have already been assigned to the project, please confirm to overwrite them: %s','<ul><li>' + projectDuplicate.join('</li><li>') + '</li></ul>'), [{
						name: 'cancel',
						label: _('Cancel upload')
					}, {
						name: 'overwrite',
						label: _('Overwrite file'),
						'default': true
					}]).then(function(response) {
						return response == 'overwrite';
					});
				}

				if (sessionDuplicate.length > 0){
					// a file with the same name has already been uploaded during this session
					return dialog.confirm(_('The following files have already been uploaded, please confirm to overwrite them: %s', '<ul><li>' + sessionDuplicate.join('</li><li>') + '</li></ul>'), [{
						name: 'cancel',
						label: _('Cancel upload')
					}, {
						name: 'overwrite',
						label: _('Overwrite file'),
						'default': true
					}]).then(function(response) {
						return response == 'overwrite';
					});
				}

				// everything OK :)
				return true;
			});

		},

		_resetForm: function() {
			this._form.clearFormValues();
			this._form.getWidget('description').reset();
			this._form.getWidget('name').reset();

			// initiate the time/date specific form widgets
			var d = new Date();
			this._form.setValues({
				distributeType: 'manual',
				distributeDate: d,
				distributeTime: d,
				collectType: 'manual',
				collectDate: d,
				collectTime: d
			});
		},

		_save: function(values) {
			// make sure that all widgets are valid
			var invalidWidgets = this._form.getInvalidWidgets();
			if (invalidWidgets.length) {
				// focus to the first invalid widget
				this._form.getWidget(invalidWidgets[0]).focus();
				return false;
			}

			this.standby(true);
			this._form.save().then(lang.hitch(this, function(result) {
				this.standby(false);
				if (result && !result.success) {
					// display error message
					dialog.alert(result.details);
					return;
				}
				this.onClose();
				return;
			}), lang.hitch(this, function(error) {
				// server error
				this.standby(false);
			}));
		},

		load: function(id) {
			// during loading show the standby animation
			this.standby(true);
			this._resetForm();

			this._footerButtons.submit.set('label', _('Save changes'));

			// the project directory name cannot be modified
			this._form.getWidget('name').set('disabled', true);

			// load the object into the form... the load method returns a
			// Deferred object in order to handel asynchronity
			this._form.load(id).then(lang.hitch(this, function() {
				// done, switch of the standby animation
				this.standby(false);
			}), lang.hitch(this, function() {
				// error handler: switch of the standby animation
				// error messages will be displayed automatically
				this.standby(false);
			}));
		},

		newObject: function() {
			this._form.getWidget('name').set('disabled', false);
			this._resetForm();
			this._footerButtons.submit.set('label', _('Create project'));
		},

		onClose: function(dn, objectType) {
			// event stub
		}
	});

});
