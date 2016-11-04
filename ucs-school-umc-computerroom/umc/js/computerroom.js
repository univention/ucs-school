/*
 * Copyright 2012-2016 Univention GmbH
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
/*global define window require console*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/aspect",
	"dojo/dom",
	"dojo/dom-class",
	"dojo/Deferred",
	"dojo/data/ItemFileWriteStore",
	"dojo/store/DataStore",
	"dojo/store/Memory",
	"dojo/promise/all",
	"dijit/ProgressBar",
	"dijit/Dialog",
	"dijit/Tooltip",
	"dojox/html/styles",
	"dojox/html/entities",
	"umc/dialog",
	"umc/tools",
	"umc/app",
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
	"umc/i18n!umc/modules/computerroom"
], function(declare, lang, array, aspect, dom, domClass, Deferred, ItemFileWriteStore, DataStore, Memory, all, DijitProgressBar,
            Dialog, Tooltip, styles, entities, dialog, tools, app, Grid, Button, Module, Page, Form,
            ContainerWidget, Text, ComboBox, ProgressBar, ScreenshotView, SettingsDialog, _) {

	// prepare CSS rules for module
	var iconPath = require.toUrl('dijit/themes/umc/icons/16x16');
	styles.insertCssRule('.umc .dojoxGridCell .dijitButtonText', 'text-decoration: none;');
	styles.insertCssRule('.umcIconCollectFiles', lang.replace('background-image: url({path}/computerroom-icon-collect-files.png); width: 16px; height: 16px;', { path: iconPath }));
	styles.insertCssRule('.umcIconFinishExam', lang.replace('background-image: url({path}/computerroom-icon-finish-exam.png); width: 16px; height: 16px;', { path: iconPath }));
	styles.insertCssRule('.umcRedColor, .umcRedColor .dijitButtonText', 'color: red!important;');

	var isConnected = function(item) { return item.connection[0] == 'connected'; };
	var isUCC = function(item) { return item.objectType[0] === 'computers/ucc'; };
	var filterUCC = function(items) { return array.filter(items, function(item) { return !isUCC(item); }); };
	var alert_UCC_unavailable = function(items) {
		var clients = array.filter(items, lang.clone(isUCC));
		if (clients.length) {
			dialog.alert(_('The action is unavailable for UCC computers.<br>The following computers will be omitted: %s', array.map(clients, function(comp) { return comp.id[0]; }).join(', ')));
		}
	};

	var disabledUCCActions = ['screenshot', 'logout', 'computerShutdown', 'computerRestart', 'demoStart', 'viewVNC'];
	var checkUCC = function(action, callback) {
		var _decorated = function(item) {
			if (isUCC(item) && disabledUCCActions.indexOf(action) !== -1) {
				return false;
			}
			return callback(item);
		};
		return _decorated;
	};


	return declare("umc.modules.computerroom", [ Module ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

		// make sure the computerroom module can only be opened once
		unique: true,

		// the property field that acts as unique identifier for the object
		idProperty: '$dn$',

		// holds the currently active room, can be set initially to directly open
		// the specified room when starting the module
		room: null,

		// holds information about the active room
		roomInfo: null,

		// internal reference to the grid
		_grid: null,

		// internal reference to the search page
		_searchPage: null,

		// internal reference to the detail page for editing an object
		_detailPage: null,

		// widget to stop presentation
		// _presentationWidget: null,
		// _presentationText: '',

		_progressBar: null,

		_dataStore: null,
		_objStore: null,

		_updateTimer: null,
		_examEndTimer: null,

		_screenshotView: null,
		_settingsDialog: null,

		_demo: null,

		_actions: null,

		_nUpdateFailures: 0,

		_vncEnabled: false,

		// buttons above grid
		_headActions: null,
		_headButtons: null,
		_changeSettingsLabel: null,

		uninitialize: function() {
			this.inherited(arguments);
			if (this._updateTimer !== null) {
				window.clearTimeout(this._updateTimer);
			}
			if (this._examEndTimer !== null) {
				window.clearTimeout(this._examEndTimer);
				this._examEndTimer = null;
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
				'class': 'dijitButtonText umcExamEndTimeButton',
				style: 'display: inline-block; vertical-align: middle;',
				visible: false
			}, {
				name: 'collect',
				iconClass: 'umcIconCollectFiles',
				visible: false,
				label: _('Collect results'),
				callback: lang.hitch(this, '_collectExam')
			}, {
				name: 'finishExam',
				iconClass: 'umcIconFinishExam',
				visible: false,
				label: _('Finish exam'),
				style: 'margin-right: 2.5em;',
				callback: lang.hitch(this, '_finishExam')
			}];
			this._headActions = [{
				name: 'settings',
				label: _('Change settings'),
				callback: lang.hitch(this, function() { this._settingsDialog.show(); })
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

			// define grid actions
			this._actions = [ {
				name: 'screenshot',
				label: _('Watch'),
				isContextAction: false,
//				canExecute: checkUCC('screenshot', function(item) { return isConnected(item); }),
				callback: lang.hitch(this, '_screenshot')
			}, {
				name: 'logout',
				label: _('Logout user'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('logout', function(item) {
					return isConnected(item) && item.user[0];
				}),
				callback: lang.hitch(this, '_logout')
			}, {
				name: 'computerShutdown',
				field: 'connection',
				label: _('Shutdown computer'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('computerShutdown', function(item) { return isConnected(item); }),
				callback: lang.hitch(this, '_computerChangeState', 'poweroff')
			}, {
				name: 'computerStart',
				field: 'connection',
				label: _('Switch on computer'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('computerStart', function(item) {
					return (item.connection[0] == 'disconnected' || item.connection[0] == 'error' || item.connection[0] == 'autherror' || item.connection[0] == 'offline') && item.mac[0];
				}),
				callback: lang.hitch(this, '_computerStart')
			}, {
				name: 'computerRestart',
				field: 'connection',
				label: _('Restart computer'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('computerRestart', function(item) { return isConnected(item); }),
				callback: lang.hitch(this, '_computerChangeState', 'restart')
			}, {
				name: 'lockInput',
				label: _('Lock input devices'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('lockInput', lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockInput(item, false);
				})),
				callback: lang.hitch(this, '_lockInput', true)
			}, {
				name: 'unlockInput',
				label: _('Unlock input devices'),
				isStandardAction: false,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('unlockInput', lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockInput(item, true);
				})),
				callback: lang.hitch(this, '_lockInput', false)
			}, {
				name: 'demoStart',
				label: _('Start presentation'),
				isStandardAction: false,
				isContextAction: true,
				isMultiAction: false,
				canExecute: checkUCC('demoStart', function(item) {
					return isConnected(item) && item.user[0] && item.DemoServer[0] !== true;
				}),
				callback: lang.hitch(this, '_demoStart')
			}, {
				name: 'ScreenLock',
				field: 'ScreenLock',
				label: _('Lock screen'),
				isStandardAction: true,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('ScreenLock', lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockScreen(item, false);
				})),
				callback: lang.hitch(this, '_lockScreen', true)
			}, {
				name: 'ScreenUnLock',
				field: 'ScreenLock',
				label: _('Unlock screen'),
				isStandardAction: true,
				isMultiAction: true,
				enablingMode: "some",
				canExecute: checkUCC('ScreenUnLock', lang.hitch(this, function(item) {
					return !this._demo.running && this._canExecuteLockScreen(item, true);
				})),
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
					computer: item.id[0]
				});
			}, this);
			if (plugin.state_message) {
				this.addNotification(plugin.state_message);
			}
		},

		// grid actions:

		_screenshot: function(ids, items) {
			if (!items.length) {
				items = this._grid.getSelectedItems();
			}
			items = array.filter(items, function(item) { return isConnected(item) && !isUCC(item); });
			if (items.length === 0) {
				items = this._grid.getAllItems();
				items = array.filter(items, function(item) { return isConnected(item) && !isUCC(item); });
			}
			this.selectChild(this._screenshotView);
			this._screenshotView.load(array.map(array.filter(items, function(item) {
				return isConnected(item) && !isUCC(item);
			}), function(item) {
				return {
					computer: item.id[0],
					username: item.user[0]
				};
			}));
		},

		_logout: function(ids, items) {
			alert_UCC_unavailable(items);
			items = filterUCC(items);
			if (items.length === 0) {
				return;
			}
			array.forEach(items, lang.hitch(this, function(comp) {
				this.umcpCommand('computerroom/user/logout', { computer: comp.id[0] });
			}));

			this.addNotification(_('The selected users are logging off.'));
		},

		_computerChangeState: function(state, ids, items) {
			alert_UCC_unavailable(items);
			items = filterUCC(items);
			if (items.length === 0) {
				return;
			}
			array.forEach(items, lang.hitch(this, function(comp) {
				this.umcpCommand('computerroom/computer/state', {
					computer: comp.id[0],
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
				if (comp.connection && comp.connection[0] === 'connected') {
					return; // computer is already turned on
				}
				// wait 300ms between every wake up to not cause an power breakdown
				window.setTimeout(lang.hitch(this, function() {
					this.umcpCommand('computerroom/computer/state', {
						computer: comp.id[0],
						state: 'poweron'
					});
				}), 300*i);
			}));
			this.addNotification(_('The selected computers are booting up.'));
		},

		_demoStart: function(ids, items) {
			if (isUCC(items[0])) {
				dialog.alert(_("UCC clients can not serve presentations."));
				return;
			}
			this.umcpCommand('computerroom/demo/start', { server: items[0].id[0] });
			dialog.alert(_("The presentation is starting. This may take a few moments. When the presentation server is started a column presentation is shown that contains a button 'Stop' to end the presentation."), _('Presentation'));
		},

		_canExecuteLockInput: function(comp, current_locking_state) {
			return (isConnected(comp) && // is connected?
					comp.user && comp.user[0] && // is user logged on?
					(!comp.teacher || comp.teacher[0] === false) && // is no teacher logged in?
					comp.InputLock[0] === current_locking_state); // is input lock in expected state?
		},

		_lockInput: function(lock, ids, items) {
			array.forEach(items, lang.hitch(this, function(comp) {
				if (this._canExecuteLockInput(comp, !lock)) {
					this.umcpCommand('computerroom/lock', {
						computer: comp.id[0],
						device: 'input',
						lock: lock
					});
					this._objStore.put({ id: comp.id[0], InputLock: null });
				}
			}));
			this.addNotification(lock ? _('The selected computers are being locked.') : _('The selected computers are being unlocked.'));
		},

		_canExecuteLockScreen: function(comp, current_locking_state) {
			return (isConnected(comp) && // is connected?
					comp.user && comp.user[0] && // is user logged on?
					(!comp.teacher || comp.teacher[0] === false) && // is no teacher logged in?
					comp.ScreenLock[0] === current_locking_state); // is screen lock in expected state?
		},

		_lockScreen: function(lock, ids, items) {
			array.forEach(items, lang.hitch(this, function(comp) {
				if (this._canExecuteLockScreen(comp, !lock)) {
					this.umcpCommand('computerroom/lock', {
						computer: comp.id[0],
						device: 'screen',
						lock: lock
					});
					this._objStore.put({ id: comp.id[0], ScreenLock: null });
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

			// initiate a progress bar widget
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);
		},

		_preRendering: function() {
			return all([
				this._setVncSettings(),
				this._loadPlugins()
			]);
		},

		_renderPages: function() {
			// render the page containing search form and grid
			this.renderSearchPage();
			this.renderScreenshotPage();
		},

		_setVncSettings: function() {
			// get UCR Variable for enabled VNC
			var getVncSettings = tools.ucr('ucsschool/umc/computerroom/ultravnc/enabled');
			getVncSettings.then(lang.hitch(this, function(result) {
				this._vncEnabled = tools.isTrue(result['ucsschool/umc/computerroom/ultravnc/enabled']);
			}));
			return getVncSettings;
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
			if (!this._searchPage) {
				return;
			}
			var roomInfo = this.get('roomInfo');
			if (!roomInfo) {
				// no room is selected
				this._searchPage.set('headerText', _('No room selected'));
				return;
			}

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
			this._searchPage.set('headerText', header);

			// update visibility of header buttons
			if (this._headButtons.finishExam.domNode) {
				this._headButtons.finishExam.set('visible', roomInfo && roomInfo.exam);
			}
			if (this._headButtons.collect.domNode) {
				this._headButtons.collect.set('visible', roomInfo && roomInfo.exam);
			}
			if (this._headButtons.examEndTime.domNode) {
				// FIXME: Text widget does not support visible (Bug #32823)
				this._headButtons.examEndTime.set('visible', roomInfo && roomInfo.exam);
			}
			if (!roomInfo || !roomInfo.exam) {
				this._headButtons.examEndTime.set('content', '');
			}

			// hide time period input field in settings dialog
			this._settingsDialog.set('exam', roomInfo.exam);

			// Bug #33413, remove in future!
			this._grid.layout();
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
			// render all GUI elements for the search formular and the grid

			// render the search page
			this._searchPage = new Page({
				headerText: this.description,
				helpText: _("Here you can watch the students' computers, lock the computers, show presentations, control the internet access and define the available printers and shares.")
			});

			// umc.widgets.Module is also a StackContainer instance that can hold
			// different pages (see also umc.widgets.TabbedModule)
			this.addChild(this._searchPage);

			this._updateHeader();

			//
			// data grid
			//

			// add VNC button to actionlist
			if (this._vncEnabled) {
				this._actions.push({
					name: 'viewVNC',
					label: _('VNC-Access'),
					isStandardAction: false,
					isMultiAction: false,
					canExecute: checkUCC('viewVNC', function(item) {
						return isConnected(item) && item.user[0];
					}),
					callback: lang.hitch(this, function(item) {
						window.open('/univention-management-console/command/computerroom/vnc?computer=' + item);
					})
				});
			}

			// define the grid columns
			var columns = [{
				name: 'name',
				width: '35%',
				label: _('Name'),
				formatter: lang.hitch(this, function(value, rowIndex) {
					var item = this._grid._grid.getItem(rowIndex);
					var icon = 'offline';
					var status_ = _('The computer is not running');

					if (isConnected(item)) {
						icon = 'demo-offline';
						status_ = _('Monitoring is activated');
					} else if (item.connection[0] == 'autherror') {
						status_ = _('The monitoring mode has failed. It seems that the monitoring service is not configured properly.');
					} else if (item.connection[0] == 'error') {
						status_ = _('The monitoring mode has failed. Maybe the service is not installed or the Firewall is active.');
					}
					if (item.DemoServer[0] === true) {
						icon = 'demo-server';
						status_ = _('The computer is currently showing a presentation');
					} else if (item.DemoClient[0] === true) {
						icon = 'demo-client';
						status_ = _('The computer is currently participating in a presentation');
					}
					var widget = new Text({});
					widget.set('content', lang.replace('<img src="{path}/16x16/computerroom-{icon}.png" height="16" width="16" style="float:left; margin-right: 5px" /> {value}', {
						path: require.toUrl('dijit/themes/umc/icons'),
						icon: icon,
						value: value
					}));
					this.own(widget);

					var computertype = {
						'computers/windows': _('Windows'),
						'computers/ucc': _('Univention Corporate Client') + '<br>' + _('(The computer does not support all iTALC features)')
					}[item.objectType[0]] || _('Unknown');

					var label = '<table>';
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
						ip: item.ip[0],
						lblMAC: _('MAC address'),
						mac: item.mac ? item.mac[0] : ''
					});
					var tooltip = new Tooltip({
						'class': 'umcTooltip',
						label: label,
						connectId: [ widget.domNode ]
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
				formatter: lang.hitch(this, function(v, rowIndex) {
					var item = this._grid._grid.getItem(rowIndex);
					if (isUCC(item) || !isConnected(item)) {
						return '';
					}
					var id = item.id[0];
					var label = lang.replace('<div style="display: table-cell; vertical-align: middle; width: 240px;height: 200px;"><img id="screenshotTooltip-{0}" alt="{1}" src="" style="width: 230px; display: block; margin-left: auto; margin-right: auto;"/></div>', [
						id,
						entities.encode(_('Currently there is no screenshot available. Wait a few seconds.'))
					]);

					var widget = new Button({
						label: _('Watch'),
						onClick: lang.hitch(this, function() {
							this._screenshot([id], [item]);
						})
					});
					this.own(widget);

					var tooltip = new Tooltip({
						'class': 'umcTooltip',
						label: label,
						connectId: [ widget.domNode ],
						onShow: function(target) {
							var image = dom.byId('screenshotTooltip-' + id);
							if (image) {
								image.src = '/univention-management-console/command/computerroom/screenshot?computer=' + id + '&random=' + Math.random();
							}
						}
					});
					widget.own(tooltip);

					return widget;
				})
			}];

			// generate the data grid
			this._grid = new Grid({
				actions: lang.clone(this._actions),
				columns: columns,
				cacheRowWidgets: false,
				moduleStore: new Memory(),
				sortIndex: 1,
				footerFormatter: lang.hitch(this, function(nItems, nItemsTotal) {
					var failed = 0;
					var msg = lang.replace(_('{0} computers are in this room'), [nItemsTotal]);

					if (! this._dataStore) {
						return '';
					}
					this._dataStore.fetch({
						query: '',
						onItem: lang.hitch(this, function(item) {
							if (!isConnected(item)) {
								failed += 1;
							}
						})
					});
					if (failed) {
						msg += ' ('+ lang.replace(_('{0} powered off/misconfigured'), [failed]) + ')';
					}
					return msg;
				})
			});

			// add the grid to the title pane
			this._searchPage.addChild(this._grid);

			this.addHeaderContainer();
			this._grid.watch('actions', lang.hitch(this, function() {
				this.addHeaderContainer();
			}));

			//
			// conclusion
			//

			// we need to call page's startup method manually as all widgets have
			// been added to the page container object
			this._searchPage.startup();
			this._dataStore = new ItemFileWriteStore({data: {
				identifier: 'id',
				label: 'name',
				items: []
			}});
			this._objStore = new DataStore({ store: this._dataStore, idProperty: 'id' });
			this._grid.moduleStore = this._objStore;
			this._grid._dataStore = this._dataStore;
			this._grid._grid.setStore(this._dataStore);
		},

		addHeaderContainer: function() {
			// add a toolbar for buttons above the grid
			var _containerRight = new ContainerWidget({ style: 'float: right' });
			this._grid.own(_containerRight);
			var _containerTop = new ContainerWidget({ style: 'width: 100%; padding-bottom: 5px;' });
			this._grid.own(_containerTop);
			this._headButtons = {};

			var addButtonTo = lang.hitch(this, function(container) {
				return lang.hitch(this, function(button) {
					var cls = button.type || Button;
					container.addChild(this._headButtons[button.name] = new cls(button));
					container.own(this._headButtons[button.name]);
					if (button.name == 'settings') {
						this._changeSettingsLabel = button.label;
					}
				});
			});
			array.forEach(this._headActions, addButtonTo(_containerRight));
			array.forEach(this._headActionsTop, addButtonTo(_containerTop));

			this._grid._header.addChild(_containerRight);
			this._grid._header.addChild(_containerTop, 0);
		},

		postCreate: function() {
			var room = this.get('room');
			if (room) {
				// try to auto load the specified room
				// show the changeRoom dialog on failure
				this.standbyDuring(this._acquireRoom(room, false)).then(undefined, lang.hitch(this, 'changeRoom'));
			} else {
				// no auto load of a specific room, try to guess one
				this.standbyDuring(this._guessRoomOfTeacher()).then(
					lang.hitch(this, function(guessed) {
						this.umcpCommand('computerroom/rooms', {school: guessed.school}).then(lang.hitch(this, function(response) {
							var deferred = new Deferred();
							deferred.resolve();

							var _room;
							array.forEach(response.result, function(iroom) {
								if (iroom.id == guessed.roomdn) {
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
					}),
					lang.hitch(this, 'changeRoom')
				);
			}
		},

		_acquireRoom: function(room, promptAlert) {
			promptAlert = promptAlert === undefined || promptAlert;  // default value == true
			return tools.umcpCommand('computerroom/room/acquire', {
				room: room
			}).then(lang.hitch(this, function(response) {
				if (response.result.success === false) {
					// we could not acquire the room
					if (promptAlert) {
						// prompt a message if wanted
						if (response.result.message == 'EMPTY_ROOM') {
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
			}));
		},

		_showExamFinishedDialog: function() {
			dialog.confirm(_('The allowed time for this examination has been reached. The exam can now be extended or collected. Should be reminded again in 5 minutes?'), [{
				name: 'remember',
				label: _('Remind again'),
				'default': true,
				callback: lang.hitch(this, function() {
					this._examEndTimer = window.setTimeout(lang.hitch(this, '_showExamFinishedDialog'), 5*60*1000);
				})
			}, {
				name: 'finish_exam',
				label: _('Finish exam'),
				callback: lang.hitch(this, '_finishExam')
			}, {
				name: 'dont_remember',
				label: _("Do not remind again"),
				callback: lang.hitch(this, function() {
					window.clearTimeout(this._examEndTimer);
					this._examEndTimer = null;
				})
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
				if (response == 'cancel') {
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

				// create container with spinning ProgressBar
				var container = new ContainerWidget({});
				container.addChild(new Text({
					content: _('Please wait while all exam documents are being collected.')
				}));
				container.addChild(new DijitProgressBar({
					indeterminate: true
				}));

				// start standby animation
				this.standby(false);
				this.standby(true, container);

				deferred.then(lang.hitch(this, function() {
					this.standby(false);
					container.destroyRecursive();
					dialog.alert(_("All related exam documents have been collected successfully from the students' home directories."));
				}), lang.hitch(this, function() {
					this.standby(false);
					container.destroyRecursive();
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
				if (response == 'cancel') {
					// user canceled the dialog
					return;
				}

				// start finishing the exam
				var info = this.get('roomInfo') || {};
				this.umcpCommand('schoolexam/exam/finish', {
					exam: info.exam,
					room: info.room
				});

				// create a 'real' ProgressBar
				var deferred = new Deferred();
				this._progressBar.reset(_('Finishing exam...'));
				this.standby(true, this._progressBar);
				this._progressBar.auto(
					'schoolexam/progress',
					{},
					function() {
						// when progress is finished, resolve the given Deferred object
						deferred.resolve();
					}
				);

				// things to do after finishing the exam
				deferred.then(lang.hitch(this, function() {
					// stop standby
					this.standby(false);

					// on success, prompt info to user
					if (this._progressBar.getErrors().errors.length === 0) {
						dialog.alert(_("<p>The exam has been successfully finished. All related exam documents have been collected from the students' home directories.</p><p><b>Note:</b> All computers need to be either switched off or rebooted before they can be used again for regular schooling.</p>"));
						delete info.exam;
						delete info.examDescription;
						delete info.examEndTime;
						this.set('roomInfo', info);

						// reset room settings
						this._settingsDialog.reset();
						this._settingsDialog.save();
					}
				}));
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
				_dialog.hide();
				_dialog.destroyRecursive();
				form.destroyRecursive();
			};

			// helper function to get the current room
			var _getRoom = function(roomDN) {
				var room = null;
				array.some(form.getWidget('room').getAllItems(), function(iroom) {
					if (iroom.id == roomDN) {
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
							msg += '<p>' + _('<b>Note:</b> In this computer room the exam "%s" is currently being conducted by %s.', room.examDescription, room.user) + '</p>';
						}
						else {
							msg += '<p>' + _('<b>Note:</b> In this computer room the exam "%s" is currently being written.', room.examDescription) + '</p>';
						}
					} else if (room && room.locked) {
						msg += '<p>' + _('<b>Note:</b> This computer room is currently in use by %s.', room.user) + '</p>';
					}
					form.getWidget('message').set('content', msg);
				})
			}, {
				type: Text,
				name: 'message',
				'class': 'umcSize-One'
			}];

			// define buttons and callbacks
			var buttons = [{
				name: 'submit',
				label: _('Select room'),
				style: 'float:right',
				callback: _callback
			}, {
				name: 'cancel',
				label: _('Cancel'),
				callback: _cleanup
			}];

			// generate the search form
			form = new Form({
				// property that defines the widget's position in a dijit.layout.BorderContainer
				widgets: widgets,
				layout: [ 'school', 'room', 'message' ],
				buttons: buttons
			});
			okButton = form.getButton('submit');

			// enable button when values are loaded
			var signal = null;
			signal = form.on('ValuesInitialized', function() {
				signal.remove();
				okButton.set('disabled', false);
			});

			// show the dialog
			_dialog = new Dialog({
				title: _('Select computer room'),
				content: form,
				'class': 'umcPopup',
				style: 'max-width: 400px;'
			});
			_dialog.show();
			okButton.set('disabled', true);
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
				if (response != 'takeover') {
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

			// remove all entries for the computer room
			var that = this;
			this._objStore.query().then(function(items) {
				array.forEach(items, function(iitem) {
					that._objStore.remove(iitem.id);
				});
			});

			// query new list of entries and populate store
			this.umcpCommand('computerroom/query', {
				reload: reload !== undefined ? reload : false
			}).then(lang.hitch(this, function(response) {
				this._settingsDialog.update();
				array.forEach(response.result, function(item) {
					this._objStore.put(item);
				}, this);
				this._updateTimer = window.setTimeout(lang.hitch(this, '_updateRoom', {}), 2000);
			}));
		},

		_updateRoom: function() {
			this.umcpCommand('computerroom/update', {}, false).then(lang.hitch(this, function(response) {
				var demo = false, demo_server = null, demo_user = null, demo_systems = 0;

				this._nUpdateFailures = 0; // update was successful

				if (response.result.locked) {
					// somebody stole our session...
					// break the update loop, prompt a message and ask for choosing a new room
					dialog.confirm(_('Control over the computer room has been taken by "%s", your session has been closed. In case this behaviour was not intended, please contact the other user. You can regain control over the computer room, by choosing it from the list of rooms again.', response.result.user), [{
						name: 'ok',
						label: _('Ok'),
						'default': true
					}]).then(lang.hitch(this, function() {
						this.changeRoom();
					}));
					return;
				}

				array.forEach(response.result.computers, function(item) {
					this._objStore.put(item);
				}, this);

				if (response.result.computers.length) {
					this._grid._updateFooterContent();
					this._grid._selectionChanged();
				}

				var redColor = false;
				if (response.result.settingEndsIn) {
					var labelValidUntil = lang.replace('{label} (' + _('{time} minutes') + ')', {
						time: response.result.settingEndsIn,
						label: this._changeSettingsLabel
					});
					this._headButtons.settings.set('label', labelValidUntil);
					redColor = (response.result.settingEndsIn <= 5);
				} else {
					if (this._headButtons.settings.get('label') != this._changeSettingsLabel) {
						this._headButtons.settings.set('label', this._changeSettingsLabel);
						this._settingsDialog.update();
					}
				}
				if (this._headButtons.settings.domNode) {
					domClass.toggle(this._headButtons.settings.domNode, 'umcRedColor', redColor);
				}

				var endTime = this.get('roomInfo').examEndTime;
				if (endTime) {
					endTime = endTime.split(':');
					var now = new Date();
					var delta = new Date(now.getFullYear(), now.getMonth(), now.getDate(), endTime[0], endTime[1], 0, 0) - now;
					if (this._headButtons.examEndTime.domNode) {
						domClass.toggle(this._headButtons.examEndTime.domNode, 'umcRedColor', (delta < 5*1000*60));
					}

					var content = _('Time is up');
					if (delta > 0) {
						content = (delta <= 60000) ? _('1 minute left') : _('%s minutes left', String(1+(delta / 1000 / 60)).split('.')[0]);
					}
					this._headButtons.examEndTime.set('content', content);
				}

				this._updateTimer = window.setTimeout(lang.hitch(this, '_updateRoom', {}), 2000);

				// update the grid actions
				this._dataStore.fetch({
					query: '',
					onItem: lang.hitch(this, function(item) {
						if (item.DemoServer[0] === true) {
							demo = true;
							demo_server = item.id[0];
							demo_user = item.user[0];
							demo_systems += 1;
						} else if (item.DemoClient[0] === true) {
							demo = true;
							demo_systems += 1;
						}
					})
				});

				var changed = (this._demo.running != demo || this._demo.server != demo_server);
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
					}

				}

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
