/*
 * Copyright 2012-2013 Univention GmbH
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
	"dojo/dom-class",
	"dojo/dom-style",
	"dojo/on",
	"dojo/promise/all",
	"dojo/topic",
	"dojo/Deferred",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Wizard",
	"umc/widgets/Module",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/TextArea",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/MultiUploader",
	"umc/widgets/StandbyMixin",
	"umc/widgets/ProgressBar",
	"umc/i18n!umc/modules/schoolexam"
], function(declare, lang, array, domClass, domStyle, on, all, topic, Deferred, dialog, tools, Wizard, Module, TextBox, Text, TextArea, ComboBox, MultiObjectSelect, MultiUploader, StandbyMixin, ProgressBar, _) {

	var ExamWizard = declare("umc.modules.schoolexam.ExamWizard", [ Wizard, StandbyMixin ], {
		umcpCommand: null,

		_progressBar: null,

		postMixInProperties: function() {
			this.inherited(arguments);

			this.standbyOpacity = 1.0;

			var myRules = _( 'Personal internet rules' );

			this.pages = [{
				name: 'general',
				headerText: _('Start a new exam'),
				helpText: _('<p>The UCS@school exam mode allows one to perform an exam in a computer room. During the exam, access to internet as well as to shares can be restricted, the student home directories are not accessible, either.</p><p>Please enter a name for the new exam and select the classes or workgroups that participate in the exam. A directory name is proposed automatically and can be adjusted if wanted.</p>'),
				widgets: [{
					name: 'school',
					type: ComboBox,
					description: _('Choose the school'),
					label: _('School'),
					dynamicValues: 'schoolexam/schools',
					autoHide: true
				}, {
					name: 'room',
					type: ComboBox,
					required: true,
					label: _('Computer room'),
					description: _('Choose the computer room in which the exam will take place'),
					depends: 'school',
					dynamicValues: 'computerroom/rooms'
				}, {
					name: 'name',
					type: TextBox,
					required: true,
					label: _('Exam name'),
					description: _('The name of the exam, e.g., "Math exam algrebra 02/2013".'),
					onChange: lang.hitch(this, function() {
						// update the directory name and avoid some special characters
						var name = this.getWidget('general', 'name').get('value');
						array.forEach([/\//g, /\\/g, /\?/g, /%/g, /\*/g, /:/g, /\|/g, /"/g, /</g, />/g, /\$/g, /'/g], function(ichar) {
							name = name.replace(ichar, '_');
						});

						// limit the filename length
						name = name.slice(0, 255);

						// update value
						this.getWidget('files', 'directory').set('value', name);
					})
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
						dynamicValues: 'schoolexam/schools',
						umcpCommand: this.umcpCommand,
						autoHide: true
					}, {
						type: TextBox,
						name: 'pattern',
						label: _('Search name')
					}],
					queryCommand: lang.hitch(this, function(options) {
						return this.umcpCommand('schoolexam/groups', options).then(function(data) {
							return data.result;
						});
					}),
					autoSearch: true
				}]
			}, {
				name: 'files',
				headerText: _('Upload of exam files'),
				helpText: _('Please select all necessary files for the exam and upload them one by one. These files will be distributed to all participating students. A copy of the original files will be stored in your home directory, as well. During the exam or at the end of it, the corresponding files can be collected from the students. The collected files will be stored in your home directory, as well.'),
				widgets: [{
					name: 'directory',
					type: TextBox,
					required: true,
					label: _('Directory name'),
					description: _('The name of the project directory as it will be displayed in the file system.')
				}, {
					type: MultiUploader,
					name: 'files',
					command: 'schoolexam/upload',
					label: _('Files'),
					description: _('Files that are distributed along with this exam')
					//canUpload: lang.hitch(this, '_checkFilenameUpload'),
					//canRemove: lang.hitch(this, '_checkFilenamesRemove')
				}]
			}, {
				name: 'roomSettings',
				headerText: _('Computer room settings'),
				helpText: _('Please select the access restrictions to internet as well as to shares. These settings can also be adjusted during the exam via the room settings in the module <i>Computer room</i>. Note that the student home directories are not accessible during the exam mode.'),
				widgets: [{
					type: ComboBox,
					name: 'shareMode',
					label: _('Share access'),
					description: _( 'Defines restriction for the share access' ),
					staticValues: [
						{ id: 'home', label : _('Home directory only') },
						{ id: 'all', label : _('No restrictions' ) }
					]
				}, {
					type: ComboBox,
					name: 'internetRule',
					label: _('Web access profile'),
					dynamicValues: 'schoolexam/internetrules',
					staticValues: [
						{ id: 'none', label: _( 'Default (global settings)' ) },
						{ id: 'custom', label: myRules }
					],
					onChange: lang.hitch(this, function(value) {
						this.getWidget('roomSettings', 'customRule').set( 'disabled', value != 'custom');
					})
				}, {
					type: TextArea,
					name: 'customRule',
					label: lang.replace( _( 'List of allowed web sites for "{myRules}"' ), {
						myRules: myRules
					} ),
					description: _( '<p>In this text box you can list web sites that are allowed to be used by the students. Each line should contain one web site. Example: </p><p style="font-family: monospace">univention.com<br/>wikipedia.org<br/></p>' ),
					validate: lang.hitch( this, function() {
						return !( this._form.getWidget( 'internetRule' ).get( 'value' ) == 'custom' && ! this._form.getWidget( 'customRule' ).get( 'value' ) );
					} ),
					onFocus: lang.hitch( this, function() {
						//dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode ); // FIXME
					} ),
					disabled: true
				}]
			}, {
				name: 'success',
				headerText: _('Exam succesfully prepared'),
				helpText: _('The preparation of the exam was successful. In order to proceed, press the "Open computer room" button. The selected computer room will then be opened automatically.'),
				widgets: [{
					type: Text,
					name: 'info',
					content: ''
				}]
			}, {
				name: 'error',
				headerText: _('An error ocurred'),
				helpText: _('An error occurred during the preparation of the exam. The following information will show more details about the exact error. Please retry to start the exam.'),
				widgets: [{
					type: Text,
					name: 'info',
					style: 'font-style:italic;',
					content: ''
				}]
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);

			// helper function for setting the maxupload size
			var setMaxSize = lang.hitch(this, function(maxSize) {
				// convert the value from MB to KB
				maxSize *= 1024;

				// update MultiUploader + its current umc/widgets/Uploader instance
				var uploader = this.getWidget('files', 'files');
				uploader.set('maxSize', maxSize);
				if (uploader._uploader) {
					uploader._uploader.set('maxSize', maxSize);
				}
			});

			// helper function for setting preselected values
			var setValue = lang.hitch(this, function(page, widget, value) {
				if (value) {
					this.getWidget(page, widget).setInitialValue(value);
				}
			});

			this.standby(true);
			// query max upload size via UCR
			var ucrDeferred = tools.ucr([
				'umc/server/upload/max',
				'ucsschool/exam/default/room',
				'ucsschool/exam/default/shares',
				'ucsschool/exam/default/internet'
			]).then(lang.hitch(this, function(result) {
				setMaxSize(result['umc/server/upload/max'] || 10240);
				setValue('roomSettings', 'shareMode', result['ucsschool/exam/default/shares']);
				setValue('roomSettings', 'internetRule', result['ucsschool/exam/default/internet']);

				// for the room, we need to match the given value against all available room DNs
				var roomWidget = this.getWidget('general', 'room');
				var roomName = result['ucsschool/exam/default/room'];
				roomWidget.ready().then(function() {
					var roomDN = null;
					array.forEach(roomWidget.getAllItems(), function(iitem) {
						if (iitem.id.indexOf('cn=' + roomName) == 0) {
							// we found the correct DN
							roomWidget.setInitialValue(iitem.id);
						}
					});
				});
			}), function() {
				// take a default value for maxSize
				setMaxSize(10240);
			});

			// initiate a progress bar widget
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);

			// standby animation until all form elements ready and the UCR
			// request has been finished
			var allReady = array.map(this.pages, lang.hitch(this, function(ipage) {
				return this._pages[ipage.name]._form.ready();
			}));
			allReady.push(ucrDeferred);
			all(allReady).then(lang.hitch(this, function() {
				this.standby(false);
			}));

			// adjust the label of the 'finish' button + redirect the callback
			array.forEach(['general', 'files', 'roomSettings'], lang.hitch(this, function(ipage) {
				var ibutton = this.getPage(ipage)._footerButtons.finish;
				ibutton.set('label', _('Start exam'));
				ibutton.callback = lang.hitch(this, '_startExam');
			}));

			// adjust the label of the 'finish' button on the 'success' page
			var button = this.getPage('success')._footerButtons.finish;
			button.set('label', _('Open computer room'));
		},

		_updateButtons: function(pageName) {
			this.inherited(arguments);

			// make the 'finish' buttons visible to create an exam already earlier
			// on the first pages
			if (pageName != 'general' && pageName != 'files' && pageName != 'roomSettings') {
				return;
			}
			var buttons = this._pages[pageName]._footerButtons;
			domClass.toggle(buttons.finish.domNode, 'dijitHidden', false);
			if (this.hasNext(pageName)) {
				// make sure that ther is a little space between the two buttons 'next' and 'finish'
				domStyle.set(buttons.finish.domNode, { marginLeft: '5px' });
			}
		},

		hasPrevious: function(pageName) {
			return pageName != 'error' && pageName != 'success' && pageName != 'general';
		},

		hasNext: function(pageName) {
			return pageName != 'roomSettings' && pageName != 'success';
		},

		next: function(pageName) {
			var next = this.inherited(arguments);
			if (pageName == 'error') {
				next = 'general';
			}
			return next;
		},

		canCancel: function(pageName) {
			return pageName != 'success';
		},

		_startExam: function() {
			// validate the current values
			var values = this.getValues();

			//TODO: validate user input

			// start the exam
			tools.umcpCommand('schoolexam/exam/start', values, false);

			// initiate the progress bar
			this._progressBar.reset(_('Starting the configuration process...' ));
			this.standby(false);
			this.standby(true, this._progressBar);
			var preparationDeferred = new Deferred();
			this._progressBar.auto(
				'schoolexam/progress',
				{},
				lang.hitch(this, '_preparationFinished', preparationDeferred),
				undefined,
				undefined,
				true
			);

			// reserve the computerroom and adjust its settings
			var computerRoomDeferred = tools.umcpCommand('computerroom/room/acquire', {
				room: values.room
			}).then(function() {
				return tools.umcpCommand('computerroom/settings/set', {
					internetRule: values.internetRule,
					customRule: values.customRule,
					shareMode: values.shareMode,
					printMode: 'default',
					examDescription: values.name,
					exam: values.directory
				});
			});

			all([preparationDeferred, computerRoomDeferred]).then(lang.hitch(this, function() {
				// open the computerroom and close the exam wizard
				this.standby(false);
				this._updateButtons('success');
				this.selectChild(this._pages.success);
			}), lang.hitch(this, function() {
				// error case
				this.standby(false);
				this._updateButtons('error');
				this.selectChild(this._pages.error);
			}));
		},

		_preparationFinished: function(deferred) {
			// get all error information and decide which next page to display
			deferred = deferred || new Deferred();
			var info = this._progressBar.getErrors();
			if (info.errors.length == 1) {
				// one error can be displayed as text
				this.getWidget('error', 'info').set('content', info.errors[0]);
				deferred.reject();
			}
			else if (info.errors.length > 1) {
				// display multiple errors as unordered list
				var html = '<ul>';
				array.forEach(info.errors, function(txt) {
					html += lang.replace('<li>{0}</li>\n', [txt]);
				});
				html += '</ul>';
				this.getWidget(nextPage, 'info').set('content', html);
				deferred.reject();
			}
			else {
				// no errors... we need a UMC server restart
				deferred.resolve();
			}
		},

		onFinished: function(values) {
			// open the computer room
			topic.publish('/umc/modules/open', 'computerroom', /*flavor*/ null, {
				room: values.room
			});
		}
	});

	return declare("umc.modules.schoolexam", [ Module ], {
		// internal reference to the installer
		_examWizard: null,

		buildRendering: function() {
			this.inherited(arguments);

			this._examWizard = new ExamWizard({
				umcpCommand: this.umcpCommand
			});
			this.addChild(this._examWizard);

			this._examWizard.on('finished', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
			this._examWizard.on('cancel', lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			}));
		}
	});
});
