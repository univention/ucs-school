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
/*global define window require console*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/aspect",
	"dojo/dom",
	"dojo/Deferred",
	"dojo/data/ItemFileWriteStore",
	"dojo/store/DataStore",
	"dojo/store/Memory",
	"dijit/ProgressBar",
	"dijit/Dialog",
	"dijit/Tooltip",
	"dojox/html/styles",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/ExpandingTitlePane",
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
], function(declare, lang, array, aspect, dom, Deferred, ItemFileWriteStore, DataStore, Memory, DijitProgressBar,
            Dialog, Tooltip, styles, dialog, tools, ExpandingTitlePane, Grid, Button, Module, Page, Form,
            ContainerWidget, Text, ComboBox, ProgressBar, ScreenshotView, SettingsDialog, _) {

	// prepare CSS rules for module
	var iconPath = require.toUrl('dijit/themes/umc/icons/16x16');
	styles.insertCssRule('.umcIconCollectFiles', lang.replace('background-image: url({path}/computerroom-icon-collect-files.png); width: 16px; height: 16px;', { path: iconPath }));
	styles.insertCssRule('.umcIconFinishExam', lang.replace('background-image: url({path}/computerroom-icon-finish-exam.png); width: 16px; height: 16px;', { path: iconPath }));

	return declare("umc.modules.computerroom", [ Module ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

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

		// internal reference to the form for the active profile settings
		_profileForm: null,

		// widget to stop presentation
		// _presentationWidget: null,
		// _presentationText: '',

		// internal reference to the expanding title pane
		_titlePane: null,

		_progressBar: null,

		_dataStore: null,
		_objStore: null,

		_updateTimer: null,

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
		},

		postMixInProperties: function() {
			// is called after all inherited properties/methods have been mixed
			// into the object (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			// status of demo/presentation
			this._demo = {
				running: false,
				systems: 0,
				server: null,
				user: null
			};

			// define actions above grid
			this._headActions = [{
				name: 'collect',
				iconClass: 'umcIconCollectFiles',
				style: 'float: left;',
				visible: false,
				label: _('Collect results'),
				callback: lang.hitch(this, '_collectExam')
			}, {
				name: 'finishExam',
				iconClass: 'umcIconFinishExam',
				style: 'float: left;',
				visible: false,
				label: _('Finish exam'),
				callback: lang.hitch(this, '_finishExam')
			}, {
				name: 'settings',
				style: 'padding-bottom: 10px; padding-bottom; 10px; float: right;',
				label: _('Change settings'),
				callback: lang.hitch(this, function() { this._settingsDialog.show(); })
			}, {
				name: 'select_room',
				style: 'padding-bottom: 10px; padding-bottom; 10px; float: right;',
				label: _('Change room'),
				callback: lang.hitch(this, 'changeRoom')
			}];

			var isConnected = function(item) { return item.connection[0] == 'connected'; };

			// define grid actions
			this._actions = [ {
				name: 'screenshot',
				field: 'screenshot',
				label: _('Watch'),
				isStandardAction: true,
				isMultiAction: true,
				tooltipClass: Tooltip,
				description: function(item) {
					return lang.replace('<div style="display: table-cell; vertical-align: middle; width: 240px;height: 200px;"><img id="screenshotTooltip-{0}" src="" style="width: 230px; display: block; margin-left: auto; margin-right: auto;"/></div>', item.id);
				},
				onShowDescription: function(target, item) {
					var image = dom.byId('screenshotTooltip-' + item.id[0]);
					image.src = '/umcp/command/computerroom/screenshot?computer=' + item.id[0] + '&random=' + Math.random();
				},
				canExecute: lang.clone(isConnected),
				callback: lang.hitch(this, function(ids, items) {
					if (items.length === 0) {
						items = this._grid.getAllItems();
					}
					this.selectChild(this._screenshotView);
					this._screenshotView.load(array.map(array.filter(items, function(item) {
						return item.connection[0] == 'connected';
					}), function(item) {
						return {
							computer: item.id[0],
							username: item.user[0]
						};
					}));
				})
			}, {
				name: 'logout',
				label: _('Logout user'),
				isStandardAction: false,
				isMultiAction: true,
				canExecute: function(item) {
					return item.connection[0] == 'connected' && item.user[0];
				},
				callback: lang.hitch(this, function(ids, items) {
					if (items.length === 0) {
						dialog.alert(_('No computers were select. Please select computers.'));
						return;
					}
					array.forEach(items, lang.hitch(this, function(comp) {
						this.umcpCommand('computerroom/user/logout', { computer: comp.id[0] });
					}));
					dialog.notify(_('The selected users are logging off.'));
				})
			}, {
				name: 'computerShutdown',
				field: 'connection',
				label: _('Shutdown computer'),
				isStandardAction: false,
				isMultiAction: true,
				canExecute: lang.clone(isConnected),
				callback: lang.hitch(this, function(ids, items) {
					if (items.length === 0) {
						dialog.alert(_('No computers were select. Please select computers.'));
						return;
					}
					array.forEach(items, lang.hitch(this, function(comp) {
						this.umcpCommand('computerroom/computer/state', {
							computer: comp.id[0],
							state: 'poweroff'
						});
					}));
					dialog.notify(_('The selected computers are shutting down.'));
				})
			}, {
				name: 'computerStart',
				field: 'connection',
				label: _('Switch on computer'),
				isStandardAction: false,
				isMultiAction: true,
				canExecute: function(item) {
					return (item.connection[0] == 'error' || item.connection[0] == 'autherror' || item.connection[0] == 'offline') && item.mac[0];
				},
				callback: lang.hitch(this, function(ids, items) {
					if (items.length === 0) {
						dialog.alert(_('No computers were select. Please select computers.'));
						return;
					}
					array.forEach(items, lang.hitch(this, function(comp) {
						this.umcpCommand('computerroom/computer/state', {
							computer: comp.id[0],
							state: 'poweron'
						});
					}));
					dialog.notify(_('The selected computers are booting up.'));
				})
			}, {
				name: 'computerRestart',
				field: 'connection',
				label: _('Restart computer'),
				isStandardAction: false,
				isMultiAction: true,
				canExecute: lang.clone(isConnected),
				callback: lang.hitch(this, function(ids, items) {
					if (items.length === 0) {
						dialog.alert(_('No computers were select. Please select computers.'));
						return;
					}
					array.forEach(items, lang.hitch(this, function(comp) {
						this.umcpCommand('computerroom/computer/state', {
							computer: comp.id[0],
							state: 'restart'
						});
					}));
					dialog.notify(_('The selected computers are rebooting.'));
				})
			}, {
				name: 'lockInput',
				label: lang.hitch(this, function(item) {
					if (!item) {
						return '';
					}
					if (item.InputLock) {
						if (item.InputLock[0] === true) {
							return _('Unlock input devices');
						} else if (item.InputLock[0] === false) {
							return _('Lock input devices');
						}
					}
					return _('Lock input devices');
				}),
				iconClass: lang.hitch(this, function(item) {
					if (!item) {
						return null;
					}
					if (!item.InputLock || item.InputLock[0] === null) {
						return 'umcIconLoading';
					}
					return null;
				}),
				isStandardAction: false,
				isMultiAction: false,
				canExecute: function(item) {
					return item.connection[0] == 'connected' && item.user && item.user[0] && (!item.teacher || item.teacher[0] === false) && item.InputLock;
				},
				callback: lang.hitch(this, function(ids, items) {
					var comp = items[0];
					// unclear status -> cancel operation
					if (comp.InputLock[0] === null) {
						return;
					}
					this.umcpCommand('computerroom/lock', {
						computer: comp.id[0],
						device: 'input',
						lock: comp.InputLock[0] !== true
					});
					this._objStore.put({ id: comp.id[0], InputLock: null});
				})
			}, {
				name: 'demoStart',
				label: _('Start presentation'),
				isStandardAction: false,
				isContextAction: true,
				isMultiAction: false,
				canExecute: function(item) {
					return item.connection[0] == 'connected' && item.user[0] && item.DemoServer[0] !== true;
				},
				callback: lang.hitch(this, function(ids, items) {
					this.umcpCommand('computerroom/demo/start', { server: items[0].id[0] });
					dialog.alert(_("The presentation is starting. This may take a few moments. When the presentation server is started a column presentation is shown that contains a button 'Stop' to end the presentation."), _('Presentation'));
				})
			}, {
				name: 'reconnect',
				label: _('Reinitialize monitoring'),
				isStandardAction: false,
				isContextAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, function() { this.queryRoom(true); })
			}];
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			// it is important to call the parent's buildRendering() method
			this.inherited(arguments);

			this._settingsDialog = new SettingsDialog({
				exam: false,
				umcpCommand: lang.hitch(this, 'umcpCommand')
			});

			// get UCR Variable for enabled VNC
			tools.ucr('ucsschool/umc/computerroom/ultravnc/enabled').then(lang.hitch(this, function(result) {
				this.standby(false);
				this._vncEnabled = tools.isTrue(result['ucsschool/umc/computerroom/ultravnc/enabled']);

				// render the page containing search form and grid
				this.renderSearchPage();
				this.renderScreenshotPage();
			}), lang.hitch(this, function() {
				this.standby(false);
			}));

			// initiate a progress bar widget
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);
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
			this._headButtons.finishExam.set('visible', roomInfo && roomInfo.exam);
			this._headButtons.collect.set('visible', roomInfo && roomInfo.exam);

			// hide time period input field in settings dialog
			this._settingsDialog.set('exam', roomInfo.exam);
		},

		_setRoomInfoAttr: function(roomInfo) {
			this._set('roomInfo', roomInfo);
			this._updateHeader(roomInfo);
		},

		renderScreenshotPage: function() {
			this._screenshotView = new ScreenshotView();
			this.addChild(this._screenshotView);
			this._screenshotView.on('close', lang.hitch(this, 'closeScreenView'));
		},

		renderSearchPage: function(containers, superordinates) {
			// render all GUI elements for the search formular and the grid

			// render the search page
			this._searchPage = new Page({
				headerText: this.description,
				helpText: _("Here you can watch the students' computers, lock the computers, show presentations, control the internet access and define the available printers and shares.")
			});

			// umc.widgets.Module is also a StackContainer instance that can hold
			// different pages (see also umc.widgets.TabbedModule)
			this.addChild(this._searchPage);

			// ExpandingTitlePane is an extension of dijit.layout.BorderContainer
			this._titlePane = new ExpandingTitlePane({
				title: _('Room administration')
			});
			this._searchPage.addChild(this._titlePane);

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
					canExecute: function(item) {
						return item.connection[0] == 'connected' && item.user[0];
					},
					callback: lang.hitch(this, function(item) {
						window.open('/umcp/command/computerroom/vnc?computer=' + item);
					})
				});
			}

			// define the grid columns
			var columns = [{
				name: 'name',
				width: '20%',
				label: _('Name'),
				formatter: lang.hitch(this, function(value, rowIndex) {
					var item = this._grid._grid.getItem(rowIndex);
					var icon = 'offline';
					var label = _('The computer is not running');

					if (item.connection[0] == 'connected') {
						icon = 'demo-offline';
						label = _('Monitoring is activated');
					} else if (item.connection[0] == 'autherror') {
						label = _('The monitoring mode has failed. It seems that the monitoring service is not configured properly.');
					} else if (item.connection[0] == 'error') {
						label = _('The monitoring mode has failed. Maybe the service is not installed or the Firewall is active.');
					}
					if (item.DemoServer[0] === true) {
						icon = 'demo-server';
						label = _('The computer is currently showing a presentation');
					} else if (item.DemoClient[0] === true) {
						icon = 'demo-client';
						label = _('The computer is currently participating in a presentation');
					}
					var widget = new Text({});
					widget.set('content', lang.replace('<img src="{path}/16x16/computerroom-{icon}.png" height="16" width="16" style="float:left; margin-right: 5px" /> {value}', {
						path: require.toUrl('dijit/themes/umc/icons'),
						icon: icon,
						value: value
					}));
					label = lang.replace('<table><tr><td><b>{lblStatus}</b></td><td>{status}</td></tr><tr><td><b>{lblIP}</b></td><td>{ip}</td></tr><tr><td><b>{lblMAC}</b></td><td>{mac}</td></tr></table>', {
						lblStatus: _('Status'),
						status: label,
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
					// destroy the tooltip when the widget is destroyed
					aspect.after(widget, 'destroy', function() { tooltip.destroy(); });

					return widget;
				})
			}, {
				name: 'user',
				width: '20%',
				label: _('User')
			}];

			// generate the data grid
			this._grid = new Grid({
				// property that defines the widget's position in a dijit.layout.BorderContainer,
				// 'center' is its default value, so no need to specify it here explicitely
				multiActionsAlwaysActive: true,
				region: 'center',
				actions: this._actionList(),
				columns: columns,
				cacheRowWidgets: false,
				moduleStore: new Memory(),
				footerFormatter: lang.hitch(this, function(nItems, nItemsTotal) {
					var failed = 0;
					var msg = lang.replace(_('{0} computers are in this room'), [nItemsTotal]);

					if (! this._dataStore) {
						return '';
					}
					this._dataStore.fetch({
						query: '',
						onItem: lang.hitch(this, function(item) {
							if (item.connection[0] != 'connected') {
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
			this._titlePane.addChild(this._grid);

			// // add search form to the title pane
			// this._titlePane.addChild(this._profileForm);

			// add a toolbar for buttons above the grid
			var _container = new ContainerWidget({ region: 'top' });
			this._headButtons = {};

			array.forEach(this._headActions, lang.hitch(this, function(button) {
				_container.addChild(this._headButtons[button.name] = new Button(button));
				if (button.name == 'settings') {
					this._changeSettingsLabel = button.label;
				}
			}));

			this._titlePane.addChild(_container);

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

		_actionList: function(demo) {
			var actions = null;
			if (demo === undefined) {
				demo = this._demo.running;
			}

			actions = lang.clone(this._actions);
			if (demo === false) {
				actions.push({
					name: 'ScreenLock',
					field: 'ScreenLock',
					label: lang.hitch(this, function(item) {
						if (!item) { // column title
							return '<span style="height: 0px; font-weight: normal; color: rgba(0,0,0,0);">' + _('Unlock screen') + '</span>';
						}
						if (!item.teacher || item.teacher[0] === false) {
							if (item.ScreenLock[0] === true) {
								return _('Unlock screen');
							} else if (item.ScreenLock[0] === false) {
								return _('Lock screen');
							}
						}
						return _('Lock screen');
					}),
					iconClass: lang.hitch(this, function(item) {
						if (!item) {
							return null;
						}
						if (item.ScreenLock[0] === null) {
							return 'umcIconLoading';
						}
						return null;
					}),
					isStandardAction: true,
					isMultiAction: false,
					canExecute: function(item) {
						return item.connection[0] == 'connected' && item.user && item.user[0] && (!item.teacher || item.teacher[0] === false);
					},
					callback: lang.hitch(this, function(ids, items) {
						var comp = items[0];
						this.umcpCommand('computerroom/lock', {
							computer: comp.id[0],
							device: 'screen',
							lock: comp.ScreenLock[0] !== true });
						this._objStore.put({ id: comp.id[0], ScreenLock: null });
					})
				});
				actions.push({
					name: 'demoClientStop',
					label: lang.hitch(this, function(item) {
						if (!item || item.DemoServer[0] === true) {
							return '';
						} else {
							return _('Stop presentation');
						}
					}),
					isStandardAction: false,
					isMultiAction: false,
					isContextAction: true,
					canExecute: function(item) {
						return item.connection[0] == 'connected' && item.DemoClient && item.DemoClient[0] === true;
					},
					callback: lang.hitch(this, function() {
						this.umcpCommand('computerroom/demo/stop', {});
					})
				});
			} else {
				actions.push({
					name: 'demoStop',
					label: lang.hitch(this, function(item) {
						if (!item) {
							return _('Presentation');
						} else {
							return _('Stop');
						}
					}),
					isStandardAction: true,
					isMultiAction: false,
					canExecute: function(item) {
						return item.connection[0] == 'connected' && item.DemoServer && item.DemoServer[0] === true;
					},
					callback: lang.hitch(this, function() {
						this.umcpCommand('computerroom/demo/stop', {});
					})
				});
			}

			return actions;
		},

		postCreate: function() {
			var room = this.get('room');
			if (room) {
				// try to auto load the specified room
				this.standby(true);
				this._acquireRoom(room, false).then(lang.hitch(function() {
					// success :)
					this.standby(false);
				}), lang.hitch(this, function() {
					// failure :( ... show the changeRoom dialog
					this.standby(false);
					this.changeRoom();
				}));
			}
			else {
				// no auto load of a specific room
				this.changeRoom();
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
			}));
		},

		_collectExam: function() {
			dialog.confirm(_('<p>Please confirm to collect students\' exam files.</p><p>This files will be stored in the corresponding exam folder of your home directory. It is possible to collect exam files several times during an exam.</p>'), [{
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
					dialog.alert(_('All related exam documents have been collected successfully from the students\' home directories.'));
				}), lang.hitch(this, function() {
					this.standby(false);
					container.destroyRecursive();
				}));
			}));
		},

		_finishExam: function() {
			dialog.confirm(_('<p>Please confirm to irrevocably finish the current exam.</p><p>All corresponding exam files will be collected from the students\' home directories and stored in the corresponding exam folder of your home directory.</p>'), [{
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
					if (this._progressBar.getErrors().errors.length == 0) {
						dialog.alert(_('The exam has been successfully finished. All related exam documents have been collected from the students\' home directories.'));
						delete info.exam;
						delete info.examDescription;
						this.set('roomInfo', info);

						// update room settings for normal mode in the backend
						// ... load settings first and then save them back
						this._settingsDialog.update().then(lang.hitch(this._settingsDialog, 'save'));
					}
				}));
			}));
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
					deferred = dialog.confirm(_('This computer room is currently in use by %s. You can take control over the room, however, the current teacher will be prompted a notification and its session will be closed.', room.user), [{
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
						// TODO: move under the beyond message as addition?
						msg += '<p>' + _('<b>Note:</b> This computerroom is currently in use to write the exam "%s".', room.examDescription) + '</p>';
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

		queryRoom: function(reload) {
			// stop update timer
			if (this._updateTimer) {
				window.clearTimeout(this._updateTimer);
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
				reload: reload !== undefined ? reload: false
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
				}

				if (response.result.settingEndsIn) {
					var labelValidUntil = lang.replace('{label} (' + _('{time} minutes') + ')', {
						time: response.result.settingEndsIn,
						label: this._changeSettingsLabel
					});
					this._headButtons.settings.set('label', labelValidUntil);
					this._headButtons.settings.set('style', (response.result.settingEndsIn <= 5) ? 'color: red;': 'color: inherit;');
				} else {
					if (this._headButtons.settings.get('label') != this._changeSettingsLabel) {
						this._headButtons.settings.set('label', this._changeSettingsLabel);
						this._settingsDialog.update();
					}
					this._headButtons.settings.set('style', 'color: inherit;'); // FIXME: remove instead of inherit
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
				if (this._demo.running != demo || this._demo.server != demo_server) {
					this._grid.set('actions', this._actionList(demo && demo_server !== null), true);
				}
				this._demo = {
					running: demo,
					server: demo_server,
					user: demo_user,
					systems: demo_systems
				};

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
