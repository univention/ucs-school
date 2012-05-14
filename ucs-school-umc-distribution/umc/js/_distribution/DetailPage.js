/*
 * Copyright 2011 Univention GmbH
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
/*global console MyError dojo dojox dijit umc */

dojo.provide("umc.modules._distribution.DetailPage");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.Form");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.StandbyMixin");

dojo.declare("umc.modules._distribution.DetailPage", [ umc.widgets.Page, umc.widgets.StandbyMixin, umc.i18n.Mixin ], {
	// summary:
	//		This class represents the detail view of our dummy module.

	// reference to the module's store object
	moduleStore: null,

	// reference to umcpCommand with the correct flavor
	umcpCommand: null,

	// currently active flavor of the module
	moduleFlavor: '',

	// use i18n information from umc.modules.distribution
	i18nClass: 'umc.modules.distribution',

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
		this.headerText = this._('Project properties');
		this.helpText = this._('This page allows to modify properties of an existing or new distribution project.');

		// configure buttons for the footer of the detail page
		this.footerButtons = [{
			name: 'submit',
			label: this._('Save'),
			callback: dojo.hitch(this, function() {
				this._save(this._form.gatherFormValues());
			})
		}, {
			name: 'cancel',
			label: this._('Back to overview'),
			callback: dojo.hitch(this, function() {
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
		umc.tools.ucr('umc/server/upload/max').then(dojo.hitch(this, function(result) {
			this.standby(false);
			var maxSize = result['umc/server/upload/max'] || 10240
			this.renderDetailPage(maxSize);
		}), dojo.hitch(this, function() {
			// some error occurred :/ ... take a default value
			this.standby(false);
			this.renderDetailPage(10240);
		}));
	},

	renderDetailPage: function(maxUploadSize) {
		// render the form containing all detail information that may be edited

		// specify all widgets
		var widgets = [{
			type: 'TextBox',
			name: 'description',
			label: this._('Description'),
			description: this._('The description of the teaching material project'),
			required: true
		}, {
			type: 'TextBox',
			name: 'name',
			label: this._('Directory name'),
			description: this._('The name of the project directory as it will be displayed in the file system.'),
			depends: 'description',
			required: true,
			dynamicValue: dojo.hitch(this, function(values) {
				var me = this._form.getWidget('name');
				if (me.get('disabled')) {
					// widget is disabled, do not change the value
					return me.get('value');
				}

				// we only need to avoid '/' for the filename
				return values.description.replace('/', '_');
			})
		}, {
			type: 'MultiUploader',
			name: 'files',
			command: 'distribution/upload',
			showClearButton: false,
			label: this._('Files'),
			description: this._('Files that have been added to this teaching material project'),
			maxSize: maxUploadSize * 1024, // conversion from kbyte to byte
			canUpload: dojo.hitch(this, '_checkFilenameUpload'),
			canRemove: dojo.hitch(this, '_checkFilenamesRemove')
		}, {
			type: 'MultiObjectSelect',
			name: 'recipients',
			label: this._('Members'),
			description: this._('List of groups that are marked to receive the teaching materials'),
			queryWidgets: [{
				type: 'ComboBox',
				name: 'school',
				label: this._('School'),
				dynamicValues: 'distribution/schools',
				umcpCommand: this.umcpCommand,
				autoHide: true
			}, {
				type: 'TextBox',
				name: 'pattern',
				label: this._('Search name')
			}],
			queryCommand: dojo.hitch(this, function(options) {
				return this.umcpCommand('distribution/groups', options).then(function(data) {
					return data.result;
				});
			}),
			formatter: function(dnList) {
				var tmp = dojo.map(dnList, function(i) {
					return i;
				});
				return tmp;
			},
			autoSearch: false
		}, {
			type: 'ComboBox',
			name: 'distributeType',
			label: this._('Distribution of project files'),
			description: this._('Specifies whether the project data is distributed automatically or manually.'),
			value: 'manual',
			staticValues: [{
				id: 'manual',
				label: this._('Manual distribution')
			}, {
				id: 'automatic',
				label: this._('Automatic distribution')
			}]
		}, {
			type: 'DateBox',
			name: 'distributeDate',
			label: this._('Distribution date'),
			description: this._('Date at which the project files will be distributed automatically.'),
			visible: false
		}, {
			type: 'TimeBox',
			name: 'distributeTime',
			label: this._('Distribution time'),
			description: this._('Time at which the project files will be distributed automatically.'),
			visible: false
		}, {
			type: 'ComboBox',
			name: 'collectType',
			label: this._('Collection of project files'),
			description: this._('Specifies whether the project data is collected automatically or manually.'),
			value: 'manual',
			staticValues: [{
				id: 'manual',
				label: this._('Manual collection')
			}, {
				id: 'automatic',
				label: this._('Automatic collection')
			}]
		}, {
			type: 'DateBox',
			name: 'collectDate',
			label: this._('Collection date'),
			description: this._('Date at which the project files will be collected automatically.')
		}, {
			type: 'TimeBox',
			name: 'collectTime',
			label: this._('Collection time'),
			description: this._('Time at which the project files will be collected automatically.')
		}];

		// specify the layout... additional dicts are used to group form elements
		// together into title panes
		var layout = [{
			label: this._('General'),
			layout: [ [ 'description', 'name' ] ]
		}, {
			label: this._('Distribution and collection of project files'),
			layout: [
				'distributeType', [ 'distributeDate', 'distributeTime' ],
				'collectType', [ 'collectDate', 'collectTime' ]
			]
		}, {
			label: this._('Members'),
			layout: [ 'recipients' ]
		}, {
			label: this._('Files'),
			layout: [ 'files' ]
		}];

		// create the form
		this._form = new umc.widgets.Form({
			widgets: widgets,
			layout: layout,
			moduleStore: this.moduleStore,
			scrollable: true
		});

		// add form to page... the page extends a BorderContainer, by default
		// an element gets added to the center region
		this.addChild(this._form);

		// hook to onSubmit event of the form
		this.connect(this._form, 'onSubmit', '_save');

		// manage visible/hidden elements
		this.connect(this._form.getWidget('distributeType'), 'onChange', function(value) {
			this._form.getWidget('distributeDate').set('visible', value != 'manual');
			this._form.getWidget('distributeTime').set('visible', value != 'manual');
		});
		this.connect(this._form.getWidget('collectType'), 'onChange', function(value) {
			this._form.getWidget('collectDate').set('visible', value != 'manual');
			this._form.getWidget('collectTime').set('visible', value != 'manual');
		});
	},

	_checkFilenamesRemove: function(filenames) {
		var nameWidget = this._form.getWidget('name');
		var isNewProject = !nameWidget.get('disabled');
		return this.umcpCommand('distribution/checkfiles', {
			project: isNewProject ? null : nameWidget.get('value'),
			filenames: filenames
		}).then(dojo.hitch(this, function(response) {
			// do allow removal if any file has already been distributed
			var results = response.result;
			var distributedFiles = [];
			dojo.forEach(results, function(i) {
				if (i.distributed) {
					distributedFiles.unshift(i.filename);
				}
			});
			if (distributedFiles.length > 0) {
				umc.dialog.alert(this._('The following files cannot be removed as they have already been distributed: %s', '<ul><li>' + distributedFiles.join('</li><li>') + '</li></ul>'));
				return false;
			}

			// everything OK :)
			return true;
		}));
	},

	_checkFilenameUpload: function(fileInfo) {
		var nameWidget = this._form.getWidget('name');
		var isNewProject = !nameWidget.get('disabled');
		return this.umcpCommand('distribution/checkfiles', {
			project: isNewProject ? null : nameWidget.get('value'),
			filenames: [ fileInfo.name ]
		}).then(dojo.hitch(this, function(response) {
			var result = response.result[0];
			if (result.distributed) {
				// do not allow the upload of an already distributed file
				umc.dialog.alert(this._('The file "%s" cannot be uploaded as it has already been distributed.', fileInfo.name));
				return false;
			}

			if (result.projectDuplicate) {
				// the file exists in the project, but has not been distributed yet
				return umc.dialog.confirm(this._('The file "%s" has already been assigned to the project, please confirm to overwrite it.', fileInfo.name), [{
					name: 'cancel',
					label: this._('Cancel upload')
				}, {
					name: 'overwrite',
					label: this._('Overwrite file'),
					'default': true
				}]).then(function(response) {
					return response == 'overwrite';
				});
			}

			if (result.sessionDuplicate) {
				// a file with the same name has already been uploaded during this session
				return umc.dialog.confirm(this._('The file "%s" has already been uploaded, please confirm to overwrite it.', fileInfo.name), [{
					name: 'cancel',
					label: this._('Cancel upload')
				}, {
					name: 'overwrite',
					label: this._('Overwrite file'),
					'default': true
				}]).then(function(response) {
					return response == 'overwrite';
				});
			}

			// everything OK :)
			return true;
		}));
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
		this._form.save().then(dojo.hitch(this, function(result) {
			this.standby(false);
			if (result && !result.success) {
				// display error message
				umc.dialog.alert(result.details);
				return;
			}
			this.onClose();
			return;
		}), dojo.hitch(this, function(error) {
			// server error
			this.standby(false);
		}));
	},

	load: function(id) {
		// during loading show the standby animation
		this.standby(true);

		// the project directory name cannot be modified
		this._form.getWidget('name').set('disabled', true);

		// load the object into the form... the load method returns a
		// dojo.Deferred object in order to handel asynchronity
		this._form.load(id).then(dojo.hitch(this, function() {
			// done, switch of the standby animation
			this.standby(false);
		}), dojo.hitch(this, function() {
			// error handler: switch of the standby animation
			// error messages will be displayed automatically
			this.standby(false);
		}));
	},

	newObject: function() {
		this._form.getWidget('name').set('disabled', false);
		this._resetForm();
	},

	onClose: function(dn, objectType) {
		// event stub
	}
});



