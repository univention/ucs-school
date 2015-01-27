/*
 * Copyright 2012-2014 Univention GmbH
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
/*global define window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/aspect",
	"dojo/dom-class",
	"dojo/dom-style",
	"dojo/on",
	"dojo/promise/all",
	"dojo/topic",
	"dojo/Deferred",
	"dojo/when",
	"umc/dialog",
	"umc/tools",
	"umc/modules/schoolexam/RebootGrid",
	"umc/widgets/Wizard",
	"umc/widgets/Module",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/TextArea",
	"umc/widgets/ComboBox",
	"umc/widgets/TimeBox",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/MultiUploader",
	"umc/widgets/StandbyMixin",
	"umc/widgets/ProgressBar",
	"umc/i18n!umc/modules/schoolexam"
], function(declare, lang, array, aspect, domClass, domStyle, on, all, topic, Deferred, when, dialog, tools, RebootGrid, Wizard, Module,
			TextBox, Text, TextArea, ComboBox, TimeBox, MultiObjectSelect, MultiUploader, StandbyMixin, ProgressBar, _) {
	// helper function that sanitizes a given filename
	var sanitizeFilename = function(name) {
		array.forEach([/\//g, /\\/g, /\?/g, /%/g, /\*/g, /:/g, /\|/g, /"/g, /</g, />/g, /\$/g, /'/g], function(ichar) {
			name = name.replace(ichar, '_');
		});

		// limit the filename length
		return name.slice(0, 255);
	};

	var ExamWizard = declare("umc.modules.schoolexam.ExamWizard", [ Wizard, StandbyMixin ], {
		umcpCommand: null,

		_progressBar: null,

		_userPrefix: null,

		_grid: null,

		// helper function to get the currently selected room entry
		_getCurrentRoom: function() {
			// find correct room entry
			var room = null;
			var widget = this.getWidget('general', 'room');
			var value = widget.get('value');
			array.some(widget.getAllItems(), function(iitem) {
				if (iitem.id == value) {
					room = iitem;
					return true;  // break loop
				}
			});
			return room;
		},

		// helper function that returns the correct message for an locked room
		_getRoomMessage: function(room) {
			// display notification if necessary
			var msg = '';
			if (room && room.exam) {
				if (room.locked) {
					msg = _('In this computer room the exam "%s" is currently being executed by %s.', room.examDescription, room.user);
				}
				else {
					msg = _('In this computer room the exam "%s" is currently being written.', room.examDescription);
				}
			} else if (room && room.locked) {
				msg =  _('This computer room is currently in use by %s.', room.user);
			}
			return msg;
		},

		postMixInProperties: function() {
			this.inherited(arguments);

			this.standbyOpacity = 1.0;

			var myRules = _( 'Personal internet rules' );

			this.pages = [{
				name: 'general',
				headerText: _('Start a new exam'),
				helpText: _('<p>The UCS@school exam mode allows one to perform an exam in a computer room. During the exam, access to internet as well as to shares can be restricted, the student home directories are not accessible, either.</p><p>Please enter a name for the new exam, specify its end time, and select classes or workgroups that shall participate in the exam.</p>'),
				layout: [
					'school',
					['room', 'info'],
					'name',
					'examEndTime',
					'recipients'
				],
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
					dynamicValues: 'computerroom/rooms',
					onChange: lang.hitch(this, function(value) {
						if (!value) {
							return;
						}

						// update the info widget to warn if a room is already in use
						var msg = this._getRoomMessage(this._getCurrentRoom());
						if (msg) {
							msg = lang.replace('<b>{note}:</b> {msg}', {
								note: _('Note'),
								msg: this._getRoomMessage(this._getCurrentRoom())
							});
						}

						// update content + visibilty of the widget
						var infoWidget = this.getWidget('general', 'info');
						infoWidget.set('content', msg || '');
						infoWidget.set('visible', Boolean(msg));
					})
				}, {
					name: 'info',
					type: Text,
					label: '&nbsp;',
					content: '',
					'class': 'umcSize-One umcText',
					style: 'padding-left: 0.4em;'
				}, {
					name: 'name',
					type: TextBox,
					required: true,
					label: _('Exam name'),
					description: _('The name of the exam, e.g., "Math exam algrebra 02/2013".'),
					onChange: lang.hitch(this, function() {
						// update the directory name
						var name = sanitizeFilename(this.getWidget('general', 'name').get('value'));
						this.getWidget('files', 'directory').set('value', name);
					})
				}, {
					name: 'examEndTime',
					type: TimeBox,
					label: _('End time'),
					description: _('The time when the exam ends')
				}, {
					type: MultiObjectSelect,
					name: 'recipients',
					required: true,
					dialogTitle: _('Assign classes/workgroups'),
					label: _('Assigned classes/workgroups'),
					description: _('Groups that are participating in the exam'),
					queryWidgets: [{
						type: ComboBox,
						name: 'school',
						label: _('School'),
						dynamicValues: 'schoolexam/schools',
						umcpCommand: lang.hitch(this, 'umcpCommand'),
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
				helpText: _('<p>Please choose a suiting directory name for the exam and upload all necessary files one by one.</p><p>These files will be distributed to all participating students. A copy of the original files will be stored in your home directory. At any moment during the exam, it is possible to collect the student files. The collected files will be stored in the exam directory of your home directory.</p>'),
				widgets: [{
					name: 'directory',
					type: TextBox,
					required: true,
					label: _('Directory name'),
					description: _('The name of the project directory as it will be displayed in the file system. The following special characters are not allowed: "/", "\\", "?", "%", "*", ":", "|", """, "<", ">", "$", "\'".'),
					validator: function(value) {
						return value == sanitizeFilename(value) && value.length > 0;
					}
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
				helpText: _('Please select the access restrictions to internet as well as to shares. These settings can also be adjusted during the exam via the room settings in the module <i>Computer room</i>. The participating students are not able to access the home directories during the exam.'),
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
						return !( this.getWidget( 'roomSettings', 'internetRule' ).get( 'value' ) == 'custom' && ! this.getWidget( 'roomSettings', 'customRule' ).get( 'value' ) );
					} ),
					onFocus: lang.hitch( this, function() {
						//dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode ); // FIXME
					} ),
					disabled: true
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
			}, {
				name: 'success',
				headerText: _('Exam succesfully prepared'),
				helpText: '...', // will be set dynamically after querying the exam prefix UCR variable
				widgets: [{
					type: Text,
					name: 'info',
					content: ''
				}]
			}, {
				name: 'reboot',
				headerText: _('Reboot student computers'),
				helpText: _('<p>For the correct functioning of the exam mode, it is important that all student computers in the computer room are rebooted. The listed computers can be automatically rebooted by pressing the button <i>Reboot computers</i>.</p><p><b>Attention:</b> No warning will be displayed to currently logged in users! The reboot will be executed immediately.</p>')
			}, {
				name: 'finished',
				headerText: _('Preparation finished'),
				helpText: _('The preparation of the exam has been finished successfully. Press the button "Open computer room" to finish this wizard and open selected computer room directly.')
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
				'ucsschool/ldap/default/userprefix/exam',
				'ucsschool/exam/default/room',
				'ucsschool/exam/default/shares',
				'ucsschool/exam/default/internet',
				'ucsschool/exam/delay/min',
				'ucsschool/exam/delay/max',
				'ucsschool/exam/delay/offset'
			]).then(lang.hitch(this, function(result) {
				// cache the user prefix and update help text
				this._userPrefix = result['ucsschool/ldap/default/userprefix/exam'] || 'exam-';
				this.getPage('success').set('helpText', _('<p>The preparation of the exam was successful. A summary of the exam properties is displayed below.<p><p>As next step, it is necessary to reboot computers in the room.</p><p><b>Attention:</b> For the exam, students are required to login with a special user account by adding <i>%(prefix)s</i> to their common username, e.g., <i>%(prefix)sjoe123</i> instead of <i>joe123</i>.</p>', { prefix: this._userPrefix })),

				// max upload size and some form values
				setMaxSize(result['umc/server/upload/max'] || 10240);
				setValue('roomSettings', 'shareMode', result['ucsschool/exam/default/shares']);
				setValue('roomSettings', 'internetRule', result['ucsschool/exam/default/internet']);

				// save delay values for the grid
				this._grid.set('minUpdateDelay', result['ucsschool/exam/delay/min'] || 30);
				this._grid.set('maxUpdateDelay', result['ucsschool/exam/delay/max'] || 120);
				this._grid.set('offsetUpdateDelay', result['ucsschool/exam/delay/offset'] || 20);

				// for the room, we need to match the given value against all available room DNs
				var roomWidget = this.getWidget('general', 'room');
				var roomName = result['ucsschool/exam/default/room'];
				roomWidget.ready().then(function() {
					var roomDN = null;
					array.forEach(roomWidget.getAllItems(), function(iitem) {
						if (iitem.id.indexOf('cn=' + roomName) === 0) {
							// we found the correct DN
							roomWidget.setInitialValue(iitem.id);
						}
					});
				});
			}), function() {
				// take a default value for maxSize
				setMaxSize(10240);
			});

			// create the grid for rebooting computers manually
			var rebootPage = this.getPage('reboot');
			this._grid = new RebootGrid({
				umcpCommand: lang.hitch(this, 'umcpCommand')
			});
			rebootPage.addChild(this._grid);

			// get value for lesson end time
			var endTimeDeferred = this.umcpCommand('schoolexam/lesson_end');
			endTimeDeferred.then(lang.hitch(this, function(data) {
				this.getWidget('examEndTime').set('value', data.result);
			}));

			// initiate a progress bar widget
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);

			// standby animation until all form elements ready and the UCR
			// request has been finished
			var allReady = array.map(this.pages, lang.hitch(this, function(ipage) {
				var page = this._pages[ipage.name];
				if (page._form) {
					return page._form.ready();
				}
				return null;
			}));
			allReady.push(ucrDeferred);
			allReady.push(endTimeDeferred);
			all(allReady).then(lang.hitch(this, function() {
				this.standby(false);
			}));

			// adjust the label of the 'finish' button + redirect the callback
			array.forEach(['general', 'files', 'roomSettings'], lang.hitch(this, function(ipage) {
				var ibutton = this.getPage(ipage)._footerButtons.finish;
				ibutton.set('label', ipage == 'roomSettings' ? _('Start exam') : _('Quick start'));
				ibutton.callback = lang.hitch(this, '_startExam');
			}));

			// disable the 'next' button on the reboot page
			var button = this.getPage('reboot')._footerButtons.next;
			button.set('disabled', true);

			// adjust the label of the 'finish' button on the 'finished' page
			button = this.getPage('finished')._footerButtons.finish;
			button.set('label', _('Open computer room'));
		},

		postCreate: function() {
			this.inherited(arguments);

			// hook when reboot page is shown
			aspect.after(this.getPage('reboot'), '_onShow', lang.hitch(this, function() {
				// find computers that need to be restarted
				var values = this.getValues();
				this._grid.monitorRoom(values.room);

				// disable the next button and reset its label
				var button = this.getPage('reboot')._footerButtons.next;
				button.set('disabled', true);
				button.set('label', _('Next'));

				// call the grid's resize method (decoupled via setTimeout)
				window.setTimeout(lang.hitch(this, function() {
					this._grid.resize();
				}, 0));
			}));

			// hook when success page is shown
			aspect.after(this.getPage('success'), '_onShow', lang.hitch(this, function() {
				var values = this.getValues();
				var html = '<table style="border-spacing:7px; border:none;">';
				array.forEach(['name', 'room', 'examEndTime', 'recipients', 'directory', 'files', 'shareMode', 'internetRule'], lang.hitch(this, function(ikey) {
					var widget = this.getWidget(ikey);
					var value = values[ikey];

					// convert all values to arrays (makes handling easier)
					if (!(value instanceof Array)) {
						value = [value];
					}

					// for ComboBoxes/MultiObjectSelect -> get the label of the chosen value 
					var newValue = value;
					if (widget.getAllItems) {
						newValue = [];
						newValue = array.map(value, function(ival) {
							var jval = ival;
							array.some(widget.getAllItems(), function(iitem) {
								if (iitem.id == ival) {
									// found correct match -> break loop
									jval = iitem.label;
									return true;
								}
							});
							return jval;
						});
					}

					// update HTML table for summary
					html += lang.replace('<tr><td style="border:none; width:160px;"><b>{label}:</b></td><td style="border:none;">{value}</td></tr>',{
						label: widget.get('label'),
						value: newValue.join(', ')
					});
				}));
				html += '</table>';

				// view table
				this.getWidget('success', 'info').set('content', html);
			}));

			// hook when monitoring of the computers has been finished
			var button = this.getPage('reboot')._footerButtons.next;
			this._grid.on('monitoringDone', lang.hitch(this, function() {
				// adjust button label and enable it
				var computers = this._grid.getComputersForReboot();
				if (computers.length) {
					button.set('label', _('Reboot computers'));
				}
				else {
					button.set('label', _('Next'));
				}
				button.set('disabled', false);
			}));
		},

		_updateButtons: function(pageName) {
			this.inherited(arguments);

			// make the 'finish' buttons visible on specific pages only
			if (array.indexOf(['general', 'files', 'roomSettings'], pageName) < 0) {
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
			return array.indexOf(['error', 'success', 'general', 'reboot'], pageName) < 0;
		},

		hasNext: function(pageName) {
			return array.indexOf(['roomSettings', 'finished'], pageName) < 0;
		},

		next: function(pageName) {
			var next = this.inherited(arguments);
			if (pageName == 'error') {
				next = 'general';
			}
			else if (pageName == 'reboot') {
				// only display a dialog in case there are computers that can be rebooted
				var connectedComputers = this._grid.getComputersForReboot();
				if (!connectedComputers.length) {
					return 'finished';
				}

				// ask user whether or not computers are rebooted
				next = dialog.confirm(_('Please confirm to reboot all computers marked as <i>Reboot necessary</i> immedialtely.'), [{
					name: 'cancel',
					label: _('Continue without reboot')
				}, {
					name: 'reboot',
					label: _('Reboot computers'),
					'default': true
				}]).then(lang.hitch(this, function(choice) {
					if (choice == 'cancel') {
						// cancel reboot action -> go directly to finish page
						return 'finished';
					}

					// reboot computers
					return this._reboot().then(function() {
						// rebooting is done -> go to the finish page
						return 'finished';
					});
				}));
			}
			return next;
		},

		canCancel: function(pageName) {
			return array.indexOf(['success', 'reboot', 'finished'], pageName) < 0;
		},

		_gotoPage: function(pageName) {
			if (!this._pages[pageName]) {
				// ignore invalid pages
				return;
			}
			this._updateButtons(pageName);
			this.selectChild(this._pages[pageName]);
		},

		_validate: function() {
			// recipients
			var values = this.getValues();
			var nextPage = null;
			if (!values.recipients.length) {
				dialog.alert(_('No recipients have been selected for the exam.'));
				nextPage = 'general';
			}

			// validate the page forms
			array.forEach(['general', 'files', 'roomSettings'], function(ipage) {
				var iform = this._pages[ipage]._form;
				if (!iform.validate() && !nextPage) {
					nextPage = ipage;
					var jform = iform;
					dialog.confirm(_('Please validate and correct your input data.'), [{
						name: 'ok',
						label: _('OK'),
						'default': true
					}]).then(lang.hitch(this, function() {
						if (jform.getInvalidWidgets().length) {
							// focus the first invalid widget
							window.setTimeout(function() {
								jform.getWidget(jform.getInvalidWidgets()[0]).focus();
							}, 500);
						}
					}));
				}
			}, this);

			var room = this._getCurrentRoom();
			if (!nextPage && room) {
				if (room.exam) {
					// block room if an exam is being written
					dialog.alert(_('The room %s cannot be chosen as the exam "%s" is currently being conducted. Please make sure that the exam is finished via the module "Computer room" before a new exam can be started again.', room.label, room.examDescription));
					nextPage = 'general';
				} else if (room.locked) {
					// room is in use -> ask user to confirm the choice
					return dialog.confirm(_('This computer room is currently in use by %s. You can take control over the room, however, the current teacher will be prompted a notification and its session will be closed.', room.user), [{
						name: 'cancel',
						label: _('Cancel'),
						'default': true
					}, {
						name: 'takeover',
						label: _('Take over')
					}]).then(lang.hitch(this, function(response) {
						if (response != 'takeover') {
							this._gotoPage('general');
							return false;
						}
						return true;
					}));
				}
			}

			return this.standbyDuring(tools.umcpCommand('schoolexam/room/validate', {room: room.id})).then(lang.hitch(this, function(data) {
				var error = data.result;
				if (error) {
					dialog.alert(error);
					nextPage = 'general';
				}
				this._gotoPage(nextPage);
				return nextPage === null;
			}));
		},

		_startExam: function() {
			when(this._validate(), lang.hitch(this, function(valid) {
				// validate the current values
				if (!valid) {
					return;
				}

				// set default error message
				this.getWidget('error', 'info').set('content', _('An unexpected error occurred.'));

				// start the exam
				var values = this.getValues();
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

				preparationDeferred.then(lang.hitch(this, function() {
					// everything fine open the computerroom and close the exam wizard
					this.standby(false);
					this._gotoPage('success');
				}), lang.hitch(this, function() {
					// handle any kind of errors
					this.standby(false);
					this._gotoPage('error');
				}));
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
				this.getWidget('error', 'info').set('content', html);
				deferred.reject();
			}
			else {
				// no errors... we need a UMC server restart
				deferred.resolve();
			}
		},

		_reboot: function() {
			// show a progress bar for rebooting the computers
			var progressBar = new ProgressBar();
			progressBar.reset(_('Rebooting computers'));
			this.own(progressBar);
			this.standby(true, progressBar);
			return this._grid.reboot().then(lang.hitch(this, function() {
				// reboot done
				this.standby(false);
			}), lang.hitch(this, function() {
				// some error happened, probably an exception due to programming error
				this.standby(false);
			}), function(percentage, computer) {
				progressBar.setInfo(null, computer, percentage);
			});
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
				umcpCommand: lang.hitch(this, 'umcpCommand')
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
