/*
 * Copyright 2012-2024 Univention GmbH
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
/*global define,window,require,console*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/io-query",
	"dojo/on",
	"dojo/topic",
	"dojo/dom",
	"dojo/dom-class",
	"dojo/Deferred",
	"dojo/store/Observable",
	"dojo/store/Memory",
	"dojo/promise/all",
	"umc/widgets/Tooltip",
	"dojox/html/styles",
	"dojox/html/entities",
	"umc/app",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Dialog",
	"umc/widgets/Grid",
	"umc/widgets/Button",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/ProgressBar",
	"umc/modules/computerroom/ScreenshotView",
	"umc/modules/computerroom/SettingsDialog",
	"umc/i18n!umc/modules/computerroom",
	"xstyle/css!./computerroom.css"
], function(declare, lang, array, ioQuery, on, topic, dom, domClass, Deferred, Observable, Memory, all,
			Tooltip, styles, entities, UMCApp, dialog, tools, Dialog, Grid, Button, Module, Page,
			Form, ContainerWidget, Text, ComboBox, ProgressBar, ScreenshotView, SettingsDialog, _) {

	var isConnected = function(item) { return item.connection === 'connected'; };

	return declare("umc.modules.computerroom", [ Module ], {
		// make sure the computerroom module can only be opened once
		unique: true,

		//flag to determine if the close module dialog was confirmed before
		toBeClosed: false,

		// the property field that acts as unique identifier for the object
		idProperty: '$dn$',

		// holds the currently active room, can be set initially to directly open
		// the specified room when starting the module
		room: null,

		// holds information about the active room
		roomInfo: null,

		// holds the flavour which should be loaded after acquiring a computerroom
		flavour: null,

		// internal reference to the grid
		_grid: null,

		// internal reference to the search page
		_searchPage: null,

		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid'
		},

		_progressBar: null,

		_dataStore: null,
		_objStore: null,
		_toScreenLock: null,
		_screenLockIntervalTime: 5000,

		_updateTimer: null,
		_examEndTimer: null,
		_screenLockTimer: null,

		_screenshotView: null,
		_settingsDialog: null,

		_demo: null,

		_actions: null,

		_nUpdateFailures: 0,

		_showRebootNote: false,

		// buttons above grid
		_headActions: null,
		_headButtons: null,
		_changeSettingsLabel: null,

		onClose: function(value) {
			if(!this.roomInfo || !this.roomInfo.exam || this.toBeClosed) {
				return true;
			}
			if(value === undefined) { // If using header button Close the function is called twice - once with param once without
				return false;
			}
			dialog.confirm(_('Do you really want to close the exam mode? FINISH EXAM finishes the exam and the results of all participants will be copied into your home directory. CONTINUE WITHOUT FINISHING closes the tab and the exam continues. By opening the computeroom module again you can return to the exam mode. Please do not forget to finish the exam at a later time.'), [
				{
					name: 'cancel',
					label: _('Cancel')
				},
				{
					name: 'continue',
					label: _('Continue without finishing'),
					style: 'margin-left: auto'
				},
				{
					name: 'finish',
					label: _('Finish exam'),
					default: true
				}
			], _('Close exam mode')).then(lang.hitch(this, function(result) {
				 if(result === 'finish') {
					this._finishExam();
				} else if (result === 'continue') {
				 	this.toBeClosed = true;
					topic.publish('/umc/tabs/close', this);
				}
			}));
			return false;
		},

		uninitialize: function() {
			this.inherited(arguments);
			if (this._updateTimer !== null) {
				window.clearTimeout(this._updateTimer);
			}
			if (this._examEndTimer !== null) {
				window.clearTimeout(this._examEndTimer);
				this._examEndTimer = null;
			}
			if (this._screenLockTimer !== null) {
				window.clearInterval(this._screenLockTimer);
				this._screenLockTimer = null;
			}
		},

		postMixInProperties: function() {
			this.inherited(arguments);

			// status of demo/presentation
			this._demo = {
				running: false,
				systems: 0,
				server: null,
				user: null
			};

			// define actions above grid
			this._headActionsTop = [{
				type: Text,
				name: 'examEndTime',
				'class': 'dijitButtonText examEndTimeNote',
				visible: false
			}, {
				name: 'collect',
				iconClass: {
					iconName: 'collect-files',
					spritePath: require.toUrl('dijit/themes/umc/icons/scalable/computerroom-icon-collect-files.svg')
				},
				visible: false,
				label: _('Collect results'),
				callback: lang.hitch(this, '_collectExam')
			}, {
				name: 'finishExam',
				iconClass: 'power',
				visible: false,
				label: _('Finish exam'),
				callback: lang.hitch(this, '_finishExam')
			}];
			this._headActions = [{
				name: 'settings',
				label: _('Change settings'),
				callback: lang.hitch(this, function() {
					this._settingsDialog.show();
				})
			}, {
				name: 'select_room',
				label: _('Change room'),
				callback: lang.hitch(this, 'changeRoom')
			}, {
				name: 'stop_presentation',
				label: _('Stop presentation'),
				visible: false,
				callback: lang.hitch(this, '_stopPresentation')
			}];

			this._actions = [ {
				name: 'screenshot',
				label: _('Watch'),
				isContextAction: false,
//				canExecute: function(item) { return isConnected(item); },
				callback: lang.hitch(this, '_screenshot')
			}, {
				name: 'logout',
				label: _('Logout user'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: function(item) {
					return isConnected(item) && item.user;
				},
				callback: lang.hitch(this, '_logout')
			}, {
				name: 'computerShutdown',
				field: 'connection',
				label: _('Shutdown computer'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: function(item) { return isConnected(item); },
				callback: lang.hitch(this, '_computerChangeState', 'poweroff')
			}, {
				name: 'computerStart',
				field: 'connection',
				label: _('Switch on computer'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: function(item) {
					return (item.connection === 'disconnected' || item.connection === 'error' || item.connection === 'autherror' || item.connection === 'offline') && item.mac;
				},
				callback: lang.hitch(this, '_computerStart')
			}, {
				name: 'computerRestart',
				field: 'connection',
				label: _('Restart computer'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: function(item) { return isConnected(item); },
				callback: lang.hitch(this, '_computerChangeState', 'restart')
			}, {
				name: 'lockInput',
				label: _('Lock input devices'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockInput(item, false);
				}),
				callback: lang.hitch(this, '_lockInput', true)
			}, {
				name: 'unlockInput',
				label: _('Unlock input devices'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockInput(item, true);
				}),
				callback: lang.hitch(this, '_lockInput', false)
			}, {
				name: 'demoStart',
				label: _('Start presentation'),
				isStandardAction: false,
				isContextAction: true,
				isMultiAction: false,
				canExecute: function(item) {
					return isConnected(item) && item.user && item.DemoServer !== true;
				},
				callback: lang.hitch(this, '_demoStart')
			}, {
				name: 'ScreenLock',
				field: 'ScreenLock',
				label: _('Lock screen'),
				isStandardAction: true,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockScreen(item, false);
				}),
				callback: lang.hitch(this, '_lockScreen', true)
			}, {
				name: 'ScreenUnLock',
				field: 'ScreenLock',
				label: _('Unlock screen'),
				isStandardAction: true,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockScreen(item, true);
				}),
				callback: lang.hitch(this, '_lockScreen', false)
			}];
		},

		_loadPlugins: function() {
			return this.umcpCommand('computerroom/plugins/load').then(lang.hitch(this, function(response) {
				array.forEach(response.result.buttons, lang.hitch(this, function(plugin) {
					this._actions.push(lang.mixin({
						isMultiAction: true,
						isStandardAction: false,
						enablingMode: 'some',
						callback: lang.hitch(this, '_executePlugin', plugin)
					}, plugin));
				}));
			}));
		},

		_executePlugin: function(plugin, ids, items) {
			if (items.length === 0) {
				dialog.alert(_('No computers were selected. Please select computers.'));
				return;
			}
			array.forEach(items, function(item) {
				this.umcpCommand('computerroom/plugins/execute', {
					plugin: plugin.name,
					computer: item.id
				});
			}, this);
			if (plugin.state_message) {
				this.addNotification(plugin.state_message);
			}
		},

		_screenshot: function(ids, items) {
			if (!items.length) {
				items = this._grid.getSelectedItems();
			}
			items = array.filter(items, function(item) { return isConnected(item); });
			if (items.length === 0) {
				items = this._grid.getAllItems();
				items = array.filter(items, function(item) { return isConnected(item); });
			}
			this.selectChild(this._screenshotView);
			this._screenshotView.load(array.map(array.filter(items, function(item) {
				return isConnected(item);
			}), function(item) {
				return {
					computer: item.id,
					username: item.user
				};
			}));
		},

		_logout: function(ids, items) {
			if (items.length === 0) {
				return;
			}
			array.forEach(items, lang.hitch(this, function(comp) {
				this.umcpCommand('computerroom/user/logout', { computer: comp.id });
			}));

			this.addNotification(_('The selected users are logging off.'));
		},

		_computerChangeState: function(state, ids, items) {
			if (items.length === 0) {
				return;
			}
			array.forEach(items, lang.hitch(this, function(comp) {
				this.umcpCommand('computerroom/computer/state', {
					computer: comp.id,
					state: state
				});
			}));

			var msg = {
				poweroff: _('The selected computers are shutting down.'),
				restart: _('The selected computers are rebooting.')
			}[state];
			if (msg) {
				this.addNotification(msg);
			}
		},

		_computerStart: function(ids, items) {
			array.forEach(items, lang.hitch(this, function(comp, i) {
				if (comp.connection && comp.connection === 'connected') {
					return; // computer is already turned on
				}
				// wait 300ms between every wake up to not cause an power breakdown
				window.setTimeout(lang.hitch(this, function() {
					this.umcpCommand('computerroom/computer/state', {
						computer: comp.id,
						state: 'poweron'
					});
				}), 300 * i);
			}));
			this.addNotification(_('The selected computers are booting up.'));
		},

		_demoStart: function(ids, items) {
			this.umcpCommand('computerroom/demo/start', { server: ids[0] });
			dialog.alert(_("The presentation is starting. This may take a few moments. When the presentation server is started a column presentation is shown that contains a button 'Stop' to end the presentation."), _('Presentation'));
		},

		_canExecuteLockInput: function(comp, current_locking_state) {
			return (isConnected(comp) && // is connected?
					comp.user && // is user logged on?
					comp.teacher === false && // is no teacher logged in?
					comp.InputLock === current_locking_state); // is input lock in expected state?
		},

		_lockInput: function(lock, ids, items) {
			array.forEach(items, lang.hitch(this, function(comp) {
				if (this._canExecuteLockInput(comp, !lock)) {
					this.umcpCommand('computerroom/lock', {
						computer: comp.id,
						device: 'input',
						lock: lock
					});
					this._objStore.put({ id: comp.id, InputLock: null });
				}
			}));
			this.addNotification(lock ? _('The selected computers are being locked.') : _('The selected computers are being unlocked.'));
		},

		_canExecuteLockScreen: function(comp, current_locking_state) {
			return (isConnected(comp) && // is connected?
					comp.user && // is user logged on?
					comp.teacher === false && // is no teacher logged in?
					comp.ScreenLock === current_locking_state); // is screen lock in expected state?
		},

		_lockScreen: function(lock, ids, items) {
			array.forEach(items, lang.hitch(this, function(comp) {
				if (this._canExecuteLockScreen(comp, !lock)) {
					if (!lock && this._toScreenLock[comp.id]) {
						delete this._toScreenLock[comp.id]
					} else if (lock) {
						this._toScreenLock[comp.id] = comp
					}
					this.umcpCommand('computerroom/lock', {
						computer: comp.id,
						device: 'screen',
						lock: lock
					});
					this._objStore.put({ id: comp.id, ScreenLock: null });
				}
			}));
			this.addNotification(lock ? _('The selected computers are being locked.') : _('The selected computers are being unlocked.'));
		},

		buildRendering: function() {
			this.inherited(arguments);

			this._settingsDialog = new SettingsDialog({
				exam: false,
				umcpCommand: lang.hitch(this, 'umcpCommand')
			});
			this.own(this._settingsDialog);

			this.standbyDuring(this._preRendering()).then(
				lang.hitch(this, '_renderPages'),
				lang.hitch(this, '_renderPages')
			);

			this._progressBar = new ProgressBar();
			this.own(this._progressBar);
		},

		_preRendering: function() {
			return all([
				this._loadUCR(),
				this._loadPlugins()
			]);
		},

		_renderPages: function() {
			// render the page containing search form and grid
			this.renderSearchPage();
			this.renderScreenshotPage();
		},

		_loadUCR: function() {
			// get UCR Variable for enabled VNC
			var getUCR = tools.ucr(['ucsschool/exam/default/show/restart', 'ucsschool/umc/computerroom/screenlock/interval']);
			getUCR.then(lang.hitch(this, function(result) {
				this._showRebootNote = tools.isTrue(result['ucsschool/exam/default/show/restart']);
				this._screenLockIntervalTime = result['ucsschool/umc/computerroom/screenlock/interval'] * 1000 || 5000;
			}));
			return getUCR;
		},

		_guessRoomOfTeacher: function() {
			var getIP = this.umcpCommand('get/ipaddress', undefined, false);
			var guessRoom = getIP.then(lang.hitch(this, function(ipaddresses) {
				return this.umcpCommand('computerroom/room/guess', {ipaddress: ipaddresses}, false);
			}));
			var roomdn = guessRoom.then(lang.hitch(this, function(response) {
				return response.result.room;  // roomdn
			}));
			var school = guessRoom.then(lang.hitch(this, function(response) {
				return response.result.school;  // OU name
			}));

			var roomGuessed = new Deferred();
			all({
				foo: getIP,
				bar: guessRoom,
				roomdn: roomdn,
				school: school
			}).then(function(result) {
				var roomdn = result.roomdn;
				if (roomdn) {
					roomGuessed.resolve({roomdn: roomdn, school: result.school});
				} else {
					roomGuessed.cancel();
				}
			}, function() {
				roomGuessed.cancel();
			});

			return roomGuessed;
		},

		startup: function() {
			this.inherited(arguments);

			// call startup for the SettingsDialog... otherwise its form values
			// cannot be queried
			this._settingsDialog.startup();
		},

		closeScreenView: function() {
			this.selectChild(this._searchPage);
		},

		_updateHeader: function() {
			if (!this._searchPage || !this._headButtons) {
				return;  // not ready yet
			}
			var roomInfo = this.get('roomInfo');
			if (!roomInfo) {
				// no room is selected
				this._searchPage.set('headerText', _('No room selected'));
				return;
			}
			this._searchPage.set('headerText', '');

			var room = tools.explodeDn(roomInfo.room, true)[0];
			room = room.replace(/^[^\-]+-/, '');
			var header = '';
			if (roomInfo.exam) {
				// exam mode
				header = _('Exam mode - %s', roomInfo.examDescription);
			}
			else {
				// normal mode
				header = _('Computer room: %s', room);
			}
//			this._searchPage.set('headerText', header);
			this.set('title', header);

			// update visibility of header buttons
			if (this._headButtons.finishExam.domNode) {
				this._headButtons.finishExam.set('visible', roomInfo && roomInfo.exam);
			}
			if (this._headButtons.collect.domNode) {
				this._headButtons.collect.set('visible', roomInfo && roomInfo.exam);
			}
			if (this._headButtons.examEndTime.domNode) {
				if (!roomInfo || !roomInfo.exam) {
					this._headButtons.examEndTime.set('content', '');
				}
				this._headButtons.examEndTime.set('visible', !!this._headButtons.examEndTime.get('content'));
			}

			// hide time period input field in settings dialog
			this._settingsDialog.set('exam', roomInfo.exam);
		},

		_setRoomInfoAttr: function(roomInfo) {
			this._set('roomInfo', roomInfo);
			this._updateHeader();
		},

		renderScreenshotPage: function() {
			this._screenshotView = new ScreenshotView();
			this.addChild(this._screenshotView);
			this._screenshotView.on('close', lang.hitch(this, 'closeScreenView'));
		},

		renderSearchPage: function() {
			this._searchPage = new Page({
				fullWidth: true,
				helpText: _("Here you can watch the students' computers, lock the computers, show presentations, control the internet access and define the available printers and shares.")
			});

			this.addChild(this._searchPage);

			var columns = [{
				name: 'name',
				width: '35%',
				label: _('Name'),
				formatter: lang.hitch(this, function(value, item) {
					var icon = 'offline';
					var status_ = _('The computer is not running');
					if (item.configurationOK) {
						if (isConnected(item)) {
							icon = 'demo-offline';
							status_ = _('Monitoring is activated');
						} else if (item.connection === 'autherror') {
							status_ = _('The monitoring mode has failed. It seems that the monitoring service is not configured properly.');
						} else if (item.connection === 'error') {
							status_ = _('The monitoring mode has failed. Maybe the service is not installed or the Firewall is active.');
						}
						if (item.DemoServer === true) {
							icon = 'demo-server';
							status_ = _('The computer is currently showing a presentation');
						} else if (item.DemoClient === true) {
							icon = 'demo-client';
							status_ = _('The computer is currently participating in a presentation');
						}
					} else {
						icon = "disconnected";
						status_ = _("The computer is unreachable because no IP address has been assigned to the computer object.");
					}

					var widget = new Text({});
					widget.set('content', lang.replace('<img src="{src}" height="16" width="16" style="float:left; margin-right: 5px" /> {value}', {
						src: require.toUrl(lang.replace('dijit/themes/umc/icons/16x16/computerroom-{0}.png', [icon])),
						value: value
					}));
					this.own(widget);

					var computertype = {
						'computers/windows': _('Windows'),
					}[item.objectType] || _('Unknown');

					var label = '<table class="computerroomComputerInfoTable">';
					label += '<tr><td><b>{lblComputerType}</b></td><td>{computertype}</td></tr>';
					label += '<tr><td><b>{lblStatus}</b></td><td>{status}</td></tr>';
					label += '<tr><td><b>{lblIP}</b></td><td>{ip}</td></tr>';
					label += '<tr><td><b>{lblMAC}</b></td><td>{mac}</td></tr></table>';

					label = lang.replace(label, {
						lblComputerType: _('Computer type'),
						computertype: computertype,
						lblStatus: _('Status'),
						status: status_,
						lblIP: _('IP address'),
						ip: item.ip,
						lblMAC: _('MAC address'),
						mac: item.mac ? item.mac : ''
					});
					var tooltip = new Tooltip({
						label: label,
						connectId: [widget.domNode]
					});
					widget.own(tooltip);

					return widget;
				})
			}, {
				name: 'user',
				width: '35%',
				label: _('User')
			}, {
				name: '_watch',
				label: ' ',
				formatter: lang.hitch(this, function(v, item) {
					if (!isConnected(item)) {
						return '';
					}
					var id = item.id;
					var label = lang.replace('<div class="screenShotView__imgTooltip--grid"><img class="screenShotView__img" alt="{1}" id="screenshotTooltip-{0}" src="" /></div>', [
						id,
						entities.encode(_('Currently there is no screenshot available. Wait a few seconds.'))
					]);

					var widget = new Button({
						label: _('Watch'),
						'class': 'ucsLinkButton',
						onClick: lang.hitch(this, function() {
							this._screenshot([id], [item]);
						})
					});
					this.own(widget);

					var tooltip = new Tooltip({
						label: label,
						connectId: [widget.domNode],
						onShow: function() {
							var image = dom.byId('screenshotTooltip-' + id);
							if (image) {
								image.src = '/univention/command/computerroom/screenshot?computer=' + encodeURIComponent(id) + '&random=' + encodeURIComponent(Math.random());
							}
						}
					});
					widget.own(tooltip);

					return widget;
				})
			}];

			this._objStore = new Observable(new Memory({ data: [], idProperty: 'id' }));

			this._grid = new Grid({
				'class': 'computerroomGrid',
				moduleStore: this._objStore,
				actions: lang.clone(this._actions),
				columns: columns,
				sortIndex: 1,
				footerFormatter: function(nItems, nItemsTotal) {
					var msg = lang.replace(_('{0} computers are in this room'), [nItemsTotal]);
					var failed = array.filter(this.getAllItems(), function(item) { return !isConnected(item); }).length;
					if (failed) {
						msg += ' ('+ lang.replace(_('{0} powered off/misconfigured'), [failed]) + ')';
					}
					return msg;
				}
			});

			this._searchPage.addChild(this._grid);

			this.addHeaderContainer();
			this._updateHeader();
		},

		addHeaderContainer: function() {
			// add a toolbar for buttons above the grid
			var _containerRight = new ContainerWidget({
				'class': 'computerroomGrid__extraButtons'
			});
			var _containerTop = new ContainerWidget({
				'class': 'computerroomGrid__examButtons'
			});
			this._headButtons = {};

			var addButtonTo = lang.hitch(this, function(container) {
				return lang.hitch(this, function(button) {
					var cls = button.type || Button;
					container.addChild(this._headButtons[button.name] = new cls(button));
					container.own(this._headButtons[button.name]);
					if (button.name === 'settings') {
						this._changeSettingsLabel = button.label;
					}
				});
			});
			array.forEach(this._headActions, addButtonTo(_containerRight));
			array.forEach(this._headActionsTop, addButtonTo(_containerTop));

			this._grid._header.addChild(_containerRight, 1);
			this._grid._header.addChild(_containerTop, 0);
		},

		postCreate: function() {
			var room = this.get('room');
			if (room) {
				// try to auto load the specified room
				// show the changeRoom dialog on failure
				this.standbyDuring(this._acquireRoom(room, false)).then(undefined, lang.hitch(this, 'changeRoom'));
				return;
			}
			// no auto load of a specific room, try to guess one
			this.standbyDuring(this._guessRoomOfTeacher()).then(lang.hitch(this, function(guessed) {
				this.umcpCommand('computerroom/rooms', {school: guessed.school}).then(lang.hitch(this, function(response) {
					var deferred = new Deferred();
					deferred.resolve();

					var _room;
					array.forEach(response.result, function(iroom) {
						if (iroom.id === guessed.roomdn) {
							_room = iroom;
						}
					});
					if (_room && _room.locked) {
						deferred = this.displayRoomTakeoverDialog(_room);
					}
					deferred.then(lang.hitch(this, function() {
						this.standbyDuring(this._acquireRoom(guessed.roomdn, true)).then(undefined, lang.hitch(this, 'changeRoom'));
					}), lang.hitch(this, 'changeRoom'));
				}));
			}), lang.hitch(this, 'changeRoom'));
		},

		_acquireRoom: function(room, promptAlert) {
			promptAlert = promptAlert === undefined || promptAlert;  // default value === true
			return tools.umcpCommand('computerroom/room/acquire', {
				room: room
			}).then(lang.hitch(this, function(response) {
				if (response.result.success === false) {
					// we could not acquire the room
					if (promptAlert) {
						// prompt a message if wanted
						if (response.result.message === 'EMPTY_ROOM') {
							dialog.alert(_('The room is empty or the computers are not configured correctly. Please select another room.'));
						}
						else {
							dialog.alert(_('Failed to open a new session for the room.'));
						}
					}
					throw new Error('Could not acquire room');
				}
				this.set('room', room);
				this.set('roomInfo', response.result.info);

				// reload the grid
				this.queryRoom();

				// update the header text containing the room
				this._grid._updateFooterContent();

				// examEndTimer dialog
				if (response.result.info.examEndTime) {
					var endTime = response.result.info.examEndTime.split(':');
					var now = new Date();
					var delta = new Date(now.getFullYear(), now.getMonth(), now.getDate(), endTime[0], endTime[1], 0, 0) - now;
					if (delta > 0) {
						this._examEndTimer = window.setTimeout(lang.hitch(this, '_showExamFinishedDialog'), delta);
					} else {
						this._showExamFinishedDialog();
					}
				}

				// read flavour from url
				var flavour = ioQuery.queryToObject(window.location.search.substring(1)).flavour || '';
				this.set('flavour', flavour);
			}));
		},

		_showExamFinishedDialog: function() {
			dialog.confirm(_('The allowed time for this examination has been reached. The exam can now be extended or collected. Should be reminded again in 5 minutes?'), [{
				name: 'remember',
				label: _('Remind again'),
				'default': true,
				callback: lang.hitch(this, function() {
					this._examEndTimer = window.setTimeout(lang.hitch(this, '_showExamFinishedDialog'), 5 * 60 * 1000);
				})
			}, {
				name: 'dont_remember',
				label: _("Do not remind again"),
				callback: lang.hitch(this, function() {
					window.clearTimeout(this._examEndTimer);
					this._examEndTimer = null;
				}),
				style: 'margin-right: auto'
			}, {
				name: 'finish_exam',
				label: _('Finish exam'),
				callback: lang.hitch(this, '_finishExam')
			}], _('Remind'));
		},

		_collectExam: function() {
			dialog.confirm(_("<p>Please confirm to collect students' exam files.</p><p>This files will be stored in the corresponding exam folder of your home directory. It is possible to collect exam files several times during an exam.</p>"), [{
				name: 'cancel',
				label: _('Cancel'),
				'default': true
			}, {
				name: 'collect',
				label: _('Collect results')
			}]).then(lang.hitch(this, function(response) {
				if (response === 'cancel') {
					// user canceled the dialog
					return;
				}

				// stop the timer
				if (this._examEndTimer) {
					window.clearTimeout(this._examEndTimer);
				}

				// start collection the files
				var info = this.get('roomInfo') || {};
				var deferred = this.umcpCommand('schoolexam/exam/collect', {
					exam: info.exam
				});

				var progressBar = new ProgressBar({});
				progressBar.setInfo(_('Please wait while all exam documents are being collected.'), null, Infinity);

				// start standby animation
				this.standbyDuring(deferred, progressBar).then(lang.hitch(this, function() {
					progressBar.destroyRecursive();
					dialog.alert(_("All related exam documents have been collected successfully from the students' home directories."));
				}), lang.hitch(this, function() {
					progressBar.destroyRecursive();
				}));
			}));
		},

		_finishExam: function() {
			dialog.confirm(_("<p>Please confirm to irrevocably finish the current exam.</p><p>All corresponding exam files will be collected from the students' home directories and stored in the corresponding exam folder of your home directory.</p>"), [{
				name: 'cancel',
				label: _('Cancel'),
				'default': true
			}, {
				name: 'finish',
				label: _('Finish exam')
			}]).then(lang.hitch(this, function(response) {
				if (response === 'cancel') {
					// user canceled the dialog
					return;
				}

				// start finishing the exam
				clearTimeout(this._updateTimer);
				this._updateRoom().then(lang.hitch(this, function () {
					var info = lang.clone(this.get('roomInfo') || {});
					if (!info.exam) {
						dialog.alert(_('There is no exam running in this room anymore. It seems like the exam was finished properly from somewhere else.'));
						return;
					}
					this.umcpCommand('schoolexam/exam/finish', {
						exam: info.exam,
						room: info.room
					});

					// create a 'real' ProgressBar
					var deferred = new Deferred();
					this._progressBar.reset(_('Finishing exam...'));
					this.standbyDuring(deferred, this._progressBar);
					this._progressBar.auto('schoolexam/progress', {}, function() {
						// when progress is finished, resolve the given Deferred object
						deferred.resolve();
					});

					// things to do after finishing the exam
					deferred.then(lang.hitch(this, function() {
						return this.umcpCommand('computerroom/exam/finish', {
							exam: info.exam,
							room: info.room
						});
					})).then(lang.hitch(this, function() {
						// on success, prompt info to user
						if (this._progressBar.getErrors().errors.length === 0) {
							var message = _("<p>The exam has been successfully finished. All related exam documents have been collected from the students' home directories.</p>");
							if (this._showRebootNote) {
								message += _("<p><b>Note:</b> All computers need to be either switched off or rebooted before they can be used again for regular schooling.</p>")
							}
							dialog.alert(message);
							delete info.exam;
							delete info.examDescription;
							delete info.examEndTime;
							this.set('roomInfo', info);

						}
					}));
				}))
			}));
		},

		_stopPresentation: function() {
			this.umcpCommand('computerroom/demo/stop', {});
			this.addNotification(_('The presentation will stop now.'));
		},

		changeRoom: function() {
			// define a cleanup function
			var _dialog = null, form = null, okButton = null;
			var _cleanup = function() {
				if (_dialog) {
					_dialog.close();
					_dialog = null;
				}
				if (form) {
					form.destroyRecursive();
					form = null;
				}
			};

			// helper function to get the current room
			var _getRoom = function(roomDN) {
				var room = null;
				array.some(form.getWidget('room').getAllItems(), function(iroom) {
					if (iroom.id === roomDN) {
						room = iroom;
						return true;
					}
					return false;
				});
				return room;
			};

			// define the callback function
			var _callback = lang.hitch(this, function(vals) {
				// default to a resolved deferred object
				var deferred = new Deferred();
				deferred.resolve();

				// show confirmation dialog if room is already locked
				var room = _getRoom(vals.room);
				if (room.locked) {
					deferred = this.displayRoomTakeoverDialog(room);
				}

				deferred = deferred.then(lang.hitch(this, function () {
					// try to acquire the session
					okButton.set('disabled', true);
					return this._acquireRoom(vals.room);
				})).then(function() {
					// destroy the dialog
					okButton.set('disabled', false);
					_cleanup();
				}, function() {
					// catch error that has been thrown to cancel chain
					okButton.set('disabled', false);
				});
			});

			// add remaining elements of the search form
			var widgets = [{
				type: ComboBox,
				name: 'school',
				description: _('Choose the school'),
				size: 'One',
				label: _('School'),
				dynamicValues: 'computerroom/schools',
				autoHide: true
			}, {
				type: ComboBox,
				name: 'room',
				label: _('Computer room'),
				description: _('Choose the computer room to monitor'),
				size: 'One',
				depends: 'school',
				dynamicValues: 'computerroom/rooms',
				onChange: lang.hitch(this, function(roomDN) {
					// display a warning in case the room is already taken
					var msg = '';
					var room = _getRoom(roomDN);
					if (room && room.exam) {
						if (room.locked) {
							msg += _('<b>Note:</b> In this computer room the exam "%s" is currently being conducted by %s.',
								entities.encode(room.examDescription),
								entities.encode(room.user)
							);
						} else {
							msg += _('<b>Note:</b> In this computer room the exam "%s" is currently being written.',
								entities.encode(room.examDescription)
							);
						}
					} else if (room && room.locked) {
						msg += _('<b>Note:</b> This computer room is currently in use by %s.', entities.encode(room.user));
					}

					var messageWidgets = form.getWidget('message');
					messageWidgets.set('content', msg);
					messageWidgets.set('visible', !!msg);
					_dialog.position();
				})
			}, {
				type: Text,
				name: 'message',
				size: 'One',
				visible: false
			}];

			var buttons = [{
				align: 'left',
				name: 'cancel',
				label: _('Cancel'),
				callback: _cleanup
			}, {
				name: 'submit',
				label: _('Select room'),
				callback: _callback
			}];

			form = new Form({
				widgets: widgets,
				layout: ['school', 'room', 'message'],
				buttons: buttons
			});
			okButton = form.getButton('submit');

			// dis-/enables submit button depending on room Combobox (setting required on room Combobox did not have desired effect)
			form.getWidget('room').on('Change', lang.hitch(this, function() {
				var submitButton = form.getButton('submit');
				room = form.getWidget('room').get('value');
				if (room) {
					submitButton.set('disabled', false);
				} else {
					submitButton.set('disabled', true);
				}
			}));

			// Check if there are any rooms to choose from. If not switch to computer room administration or just close module (via dialog)
			on.once(form, "valuesInitialized", lang.hitch(this, function() {
				var schools = form.getWidget('school').getAllItems();
				var rooms = form.getWidget("room").getAllItems();
				if (schools.length === 1 && ! rooms.length) {  // Only check for no rooms if you can only choose one school
					_cleanup();
					this.displayNoRoomsDialog();
				}
			}));


			_dialog = new Dialog({
				title: _('Select computer room'),
				content: form,
				style: 'width: 400px;'
			});
			_dialog.show();
			_dialog.standbyDuring(form.ready());
			okButton.set('disabled', true);
		},

		displayNoRoomsDialog: function() {
			var moduleAccess = UMCApp.getModule("schoolrooms");
			var openModuleSchoolrooms = lang.hitch(this, function() {
				topic.publish('/umc/modules/open', "schoolrooms", '', {_startWithCreation: true});
				closeModuleComputerroom();
			});
			var closeModuleComputerroom = lang.hitch(this, function() {
				topic.publish('/umc/tabs/close', this);
			});
			var txt = moduleAccess ?
				_('Do you want to create a computer room now or close the module?') :
				_('Please contact your system administrator for the creation of computer rooms.');
			var title = _('There are no computer rooms available');
			var options = [{name: 'close', label: _('Close module'), default: true}];
			if (moduleAccess) {
				options.push({name: 'create', label: _('Manage computer rooms')});
			}
			dialog.confirm(txt, options, title).then(lang.hitch(this, function(response) {
				if (response === 'close') {
					closeModuleComputerroom();
				} else if (response === 'create') {
					openModuleSchoolrooms();
				}
			}));
		},

		displayRoomTakeoverDialog: function(room) {
			return dialog.confirm(_('This computer room is currently in use by %s. You can take control over the room, however, the current teacher will be prompted a notification and its session will be closed.', room.user), [{
				name: 'cancel',
				label: _('Cancel'),
				'default': true
			}, {
				name: 'takeover',
				label: _('Take over')
			}]).then(function(response) {
				if (response !== 'takeover') {
					// cancel deferred chain
					throw false;
				}
			});
		},

		queryRoom: function(reload) {
			// stop update timer
			if (this._updateTimer) {
				window.clearTimeout(this._updateTimer);
			}
			if (this._examEndTimer) {
				window.clearTimeout(this._examEndTimer);
				this._examEndTimer = null;
			}
			if (this._screenLockTimer) {
				window.clearInterval(this._screenLockTimer);
				this._screenLockTimer = null;
			}

			// remove all entries for the computer room
			this._toScreenLock = {};
			this._objStore.query().forEach(lang.hitch(this, function(item) {
				this._objStore.remove(item.id);
			}));

			// query new list of entries and populate store
			this.umcpCommand('computerroom/query', {
				reload: reload !== undefined ? reload : false
			}).then(lang.hitch(this, function(response) {
				this._settingsDialog.update();
				array.forEach(response.result, function(item) {
					this._objStore.put(item);
				}, this);
				this._updateTimer = window.setTimeout(lang.hitch(this, '_updateRoom', {}), 2000);
				if (this._screenLockIntervalTime > 0) {
					this._screenLockTimer = window.setInterval(lang.hitch(this, '_screenLockInterval', {}), this._screenLockIntervalTime);
				}
			}));
		},

		_screenLockInterval: function() {
			for (var id of Object.keys(this._toScreenLock)) {
				if (this._canExecuteLockScreen(this._toScreenLock[id], false)) {
					this.umcpCommand('computerroom/lock', {
						computer: id,
						device: 'screen',
						lock: true
					});
				}
			}
		},

		_updateRoom: function() {
			return this.umcpCommand('computerroom/update', {}, false).then(lang.hitch(this, function(response) {
				var demo = false, demo_server = null, demo_user = null, demo_systems = 0;

				if (this.get('roomInfo') !== response.result.room_info) {
					this.set('roomInfo', response.result.room_info);
				}
				this._nUpdateFailures = 0; // update was successful

				if (response.result.locked) {
					// somebody stole our session...
					// break the update loop, prompt a message and ask for choosing a new room
					if (this._screenLockTimer) {
						window.clearInterval(this._screenLockTimer);
						this._screenLockTimer = null;
					}
					dialog.confirm(_('Control over the computer room has been taken by "%s", your session has been closed. In case this behaviour was not intended, please contact the other user. You can regain control over the computer room, by choosing it from the list of rooms again.', response.result.user), [{
						name: 'ok',
						label: _('Ok'),
						'default': true
					}]).then(lang.hitch(this, function() {
						this.changeRoom();
					}));
					return;
				}

				this._updateTimer = window.setTimeout(lang.hitch(this, '_updateRoom', {}), 2000);
				array.forEach(response.result.computers, function(item) {
					this._objStore.put(item);
					if (this._toScreenLock[item.id] || item.ScreenLock) {
						this._toScreenLock[item.id] = item;
					}
				}, this);

				if (response.result.computers.length) {
					this._grid._selectionChanged();
					this._grid.update(true);
				}

				var areSettingsExpiring = false;
				if (response.result.settingEndsIn) {
					var labelValidUntil = lang.replace('{label} (' + _('{time} minutes') + ')', {
						time: response.result.settingEndsIn,
						label: this._changeSettingsLabel
					});
					this._headButtons.settings.set('label', labelValidUntil);
					areSettingsExpiring = (response.result.settingEndsIn <= 5);
				} else {
					if (this._headButtons.settings.get('label') !== this._changeSettingsLabel) {
						this._headButtons.settings.set('label', this._changeSettingsLabel);
						this._settingsDialog.update();
					}
				}
				if (this._headButtons.settings.domNode) {
					domClass.toggle(this._headButtons.settings.domNode, 'computerroomSettingsButton--warning', areSettingsExpiring);
				}

				var endTime = (this.get('roomInfo') || {}).examEndTime;
				if (endTime) {
					endTime = endTime.split(':');
					var now = new Date();
					var delta = new Date(now.getFullYear(), now.getMonth(), now.getDate(), endTime[0], endTime[1], 0, 0) - now;
					if (this._headButtons.examEndTime.domNode) {
						domClass.toggle(this._headButtons.examEndTime.domNode, 'examEndTimeNote--warning', (delta < 5*1000*60));
					}

					var content = _('Time is up');
					if (delta > 0) {
						content = (delta <= 60000) ? _('1 minute left') : _('%s minutes left', String(1+(delta / 1000 / 60)).split('.')[0]);
					}
					this._headButtons.examEndTime.set('content', content);
					this._headButtons.examEndTime.set('visible', !!this._headButtons.examEndTime.get('content'));
				}

				// update the grid actions
				this._objStore.query().forEach(lang.hitch(this, function(item) {
					if (item.DemoServer === true) {
						demo = true;
						demo_server = item.id;
						demo_user = item.user;
						demo_systems += 1;
					} else if (item.DemoClient === true) {
						demo = true;
						demo_systems += 1;
					}
				}));

				var changed = (this._demo.running !== demo || this._demo.server !== demo_server);
				this._demo = {
					running: demo,
					server: demo_server,
					user: demo_user,
					systems: demo_systems
				};

				if (changed) {
					// show or hide the "stop presentation" button if already initialized
					if (this._headButtons !== null && this._headButtons.stop_presentation && this._headButtons.stop_presentation.domNode) {
						this._headButtons.stop_presentation.set('visible', demo);
						this._grid.updateActionsVisibility();
					}
				}

				// change to flavour only once
				var flavour = this.get('flavour');
				if (flavour === 'screenshot') {
					 this._screenshot(null, this._grid.getAllItems());
				}
				this.set('flavour', null);

			}), lang.hitch(this, function(err) {
				// error case, update went wrong, try to reinitiate the computer room (see Bug #27202)
				console.warn('WARN: the command "computerroom/update" failed:', err);
				this._nUpdateFailures++;
				if (this._nUpdateFailures < 5 && this.get('room')) {
					// try several times to reconnect and then give up
					this._acquireRoom(this.get('room'), false).then(function() {
						// success :) .... nothing needs to be done as _acquireRoom() takes care of anything
					}, lang.hitch(this, function() {
						// failure :( ... try again after some idle time
						this._updateTimer = window.setTimeout(lang.hitch(this, '_updateRoom', {}), 1000 * this._nUpdateFailures);
					}));
				} else {
					// fall back, automatic reinitialization failed, show initial dialog to choose a room
					this._nUpdateFailures = 0;
					this.set('room', null);
					this.changeRoom();
					dialog.alert(_('Lost the connection to the computer room. Please try to reopen the computer room.'));
				}
			}));
		}
	});
});
