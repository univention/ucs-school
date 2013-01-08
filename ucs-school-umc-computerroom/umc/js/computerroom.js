/*
 * Copyright 2012 Univention GmbH
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
/*global define window require*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/aspect",
	"dojo/dom",
	"dojo/Deferred",
	"dijit/Dialog",
	"dojo/data/ItemFileWriteStore",
	"dojo/store/DataStore",
	"dojo/store/Memory",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/Tooltip",
	"umc/modules/computerroom/ScreenshotView",
	"umc/modules/computerroom/RescheduleDialog",
	"umc/modules/computerroom/SettingsDialog",
	"umc/i18n!/umc/modules/computerroom"
], function(declare, lang, array, aspect, dom, Deferred, Dialog, ItemFileWriteStore, DataStore,
            Memory, dialog, tools, ExpandingTitlePane, Grid, Module, Page, Form, ContainerWidget,
            Text, ComboBox, Tooltip, ScreenshotView, RescheduleDialog, SettingsDialog, _) {

	return declare("umc.modules.computerroom", [ Module ], {
		// summary:
		//		Template module to ease the UMC module development.
		// description:
		//		This module is a template module in order to aid the development of
		//		new modules for Univention Management Console.

		// the property field that acts as unique identifier for the object
		idProperty: '$dn$',

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

		_profileInfo: null,
		_validTo: null,

		_dataStore: null,
		_objStore: null,

		_updateTimer: null,

		_screenshotView: null,
		_settingsDialog: null,

		_demo: null,

		_actions: null,

		_currentSchool: null,
		_currentRoom: null,

		_vncEnabled: false,

		uninitialize: function() {
			this.inherited( arguments );
			if ( this._updateTimer !== null ) {
				window.clearTimeout( this._updateTimer );
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

			var header = true;
			// define grid actions
			this._actions = [ {
				name: 'screenshot',
				field: 'screenshot',
				label: lang.hitch(this, function(item) {
					if (!item) {
						header = !header;
						if ( header ) {
							return _( 'Actions' );
						} else {
							return _( 'watch' );
						}
					}
					return _( 'watch' );
				}),
				isStandardAction: true,
				isMultiAction: true,
				description: function( item ) {
					return lang.replace( '<div style="display: table-cell; vertical-align: middle; width: 240px;height: 200px;"><img id="screenshotTooltip-{0}" src="" style="width: 230px; display: block; margin-left: auto; margin-right: auto;"/></div>', item.id );
				},
				onShowDescription: function( target, item ) {
					var image = dom.byId( 'screenshotTooltip-' + item.id[ 0 ] );
					image.src = '/umcp/command/computerroom/screenshot?computer=' + item.id[ 0 ] + '&random=' + Math.random();
				},
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected';
				},
				callback: lang.hitch(this, function( ids, items ) {
					if ( items.length === 0 ) {
						items = this._grid.getAllItems();
					}
					this.selectChild( this._screenshotView );
					this._screenshotView.load(array.map(array.filter( items, function( item ) {
						return item.connection[ 0 ] == 'connected';
					} ), function( item ) {
						return { 
							computer: item.id[ 0 ],
							username: item.user[ 0 ]
						};
					} ) );
				} )
			}, {
				name: 'logout',
				label: _('Logout user'),
				isStandardAction: false,
				isMultiAction: false,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected' && item.user[ 0 ];
				},
				callback: lang.hitch(this, function( ids, items ) {
					var comp = items[ 0 ];
					this.umcpCommand( 'computerroom/user/logout', { computer: comp.id[ 0 ] } );
				} )
			}, {
				name: 'computerShutdown',
				field: 'connection',
				label: _('Shutdown computer'),
				isStandardAction: false,
				isMultiAction: false,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected';
				},
				callback: lang.hitch(this, function( ids, items ) {
					var comp = items[ 0 ];
					this.umcpCommand( 'computerroom/computer/state', { 
						computer: comp.id[ 0 ],
						state: 'poweroff'
					} );
				} )
			}, {
				name: 'computerStart',
				field: 'connection',
				label: _('Switch on computer'),
				isStandardAction: false,
				isMultiAction: false,
				canExecute: function( item ) {
					return ( item.connection[ 0 ] == 'error' || item.connection[ 0 ] == 'autherror' || item.connection[ 0 ] == 'offline' ) && item.mac[ 0 ];
				},
				callback: lang.hitch(this, function( ids, items ) {
					var comp = items[ 0 ];
					this.umcpCommand( 'computerroom/computer/state', { 
						computer: comp.id[ 0 ],
						state: 'poweron'
					} );
				} )
			}, {
				name: 'computerRestart',
				field: 'connection',
				label: _('Restart computer'),
				isStandardAction: false,
				isMultiAction: false,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected';
				},
				callback: lang.hitch(this, function( ids, items ) {
					var comp = items[ 0 ];
					this.umcpCommand( 'computerroom/computer/state', { 
						computer: comp.id[ 0 ],
						state: 'restart'
					} );
				} )
			}, {
				name: 'lockInput',
				label: lang.hitch( this, function( item ) {
					if ( !item ) {
						return '';
					}
					if ( item.InputLock ) {
						if ( item.InputLock[ 0 ] === true ) {
							return _('Unlock input devices');
						} else if ( item.InputLock[ 0 ] === false ) {
							return _('Lock input devices');
						}
					}
					return '';
				} ),
				iconClass: lang.hitch( this, function( item ) {
					if ( !item ) {
						return null;
					}
					if ( !item.InputLock || item.InputLock[ 0 ] === null ) {
						return 'umcIconLoading';
					}
					return null;
				} ),
				isStandardAction: false,
				isMultiAction: false,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected' && item.user && item.user[ 0 ] && item.InputLock;
				},
				callback: lang.hitch(this, function( ids, items ) {
					var comp = items[ 0 ];
					// unclear status -> cancel operation
					if ( comp.InputLock[ 0 ] === null ) {
						return;
					}
					this.umcpCommand( 'computerroom/lock', {
						computer: comp.id[ 0 ],
						device : 'input',
						lock: comp.InputLock[ 0 ] !== true } );
					this._objStore.put( { id: comp.id[ 0 ], InputLock: null } );
				} )
			}, {
				name: 'demoStart',
				label: _('Start presentation'),
				isStandardAction: false,
				isContextAction: true,
				isMultiAction: false,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected' && item.user[ 0 ] && item.DemoServer[ 0 ] !== true;
				},
				callback: lang.hitch( this, function( ids, items ) {
					this.umcpCommand( 'computerroom/demo/start', { server: items[ 0 ].id[ 0 ] } );
					dialog.alert( _( "The presentation is starting. This may take a few moments. When the presentation server is started a columns presentation is shown that contains a button 'stop' to end the presentation." ), _( 'Presentation' ) );
				} )
			}, {
				name: 'reconnect',
				label: _( 'Reinitialize monitoring' ),
				isStandardAction: false,
				isContextAction: true,
				isMultiAction: false,
				callback: lang.hitch( this, function() { this.queryRoom( true ); } )
			} ];
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			// it is important to call the parent's buildRendering() method
			this.inherited(arguments);

			this._rescheduleDialog = new RescheduleDialog( {
				umcpCommand: lang.hitch( this.umcpCommand )
			} );
			this._settingsDialog = new SettingsDialog( {
				umcpCommand: lang.hitch( this.umcpCommand )
			} );

			this._rescheduleDialog.on('PeriodChanged', lang.hitch( this._settingsDialog, function( value ) {
				this._form.getWidget( 'period' ).set( 'value', value ) ;
			} ) );
			this._settingsDialog.on('PeriodChanged', lang.hitch( this._rescheduleDialog, function( value ) {
				this._form.getWidget( 'period' ).set( 'value', value ) ;
			} ) );

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
		},

		closeScreenView: function() {
			this.selectChild( this._searchPage );
		},

		_updateHeader: function( room ) {
			if ( room ) {
				room = tools.explodeDn( room, true )[ 0 ];
				room = room.replace( /^[^\-]+-/, '' );
			} else {
				room = _('No room selected');
			}
			var label = lang.replace('{roomLabel}: {room} ' +
					'(<a href="javascript:void(0)" ' +
					'onclick=\'dijit.byId("{id}").changeRoom()\'>{changeLabel}</a>)', {
				roomLabel: _('Room'),
				room: room,
				changeLabel: _('select room'),
				id: this.id
			});
			this._titlePane.set( 'title', label );
		},

		renderScreenshotPage: function() {
			this._screenshotView = new ScreenshotView();
			this.addChild( this._screenshotView );
			this._screenshotView.on('close', lang.hitch(this, 'closeScreenView'));
		},

		renderSearchPage: function(containers, superordinates) {
			// render all GUI elements for the search formular and the grid

			// render the search page
			this._searchPage = new Page({
				headerText: this.description,
				helpText: _( "Here you can watch the student's computers, locking the computers, show presentations, control the internet access and define the available printers and shares." )
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
					canExecute: function( item ) {
						return item.connection[ 0 ] == 'connected' && item.user[ 0 ];
					},
					callback: lang.hitch(this, function( item ) {
						window.open('/umcp/command/computerroom/vnc?computer=' + item);
					})
				});
			}

			// define the grid columns
			var columns = [{
				name: 'name',
				label: _('Name'),
				formatter: lang.hitch( this, function( value, rowIndex ) {
					var item = this._grid._grid.getItem( rowIndex );
					var icon = 'offline';
					var label = _( 'The computer is not running' );

					if ( item.connection[ 0 ] == 'connected' ) {
						icon = 'demo-offline';
						label = _( 'Monitoring is activated' );
					} else if ( item.connection[ 0 ] == 'autherror' ) {
						label = _( 'The monitoring mode has failed. It seems that the monitoring service is not configured properly.' );
					} else if ( item.connection[ 0 ] == 'error' ) {
						label = _( 'The monitoring mode has failed. Maybe the service is not installed or the Firewall is active.' );
					}
					if ( item.DemoServer[ 0 ] === true ) {
						icon = 'demo-server';
						label = _( 'The computer is showing a presentation currently' );
					} else if ( item.DemoClient[ 0 ] === true ) {
						icon = 'demo-client';
						label = _( 'The computer is participating in a  presentation currently' );
					}
					var widget = new Text({});
					widget.set( 'content', lang.replace( '<img src="{path}/16x16/computerroom-{icon}.png" height="16" width="16" style="float:left; margin-right: 5px" /> {value}', {
						path: require.toUrl('dijit/themes/umc/icons'),
						icon: icon,
						value: value
					} ) );
					label = lang.replace( '<table><tr><td><b>{lblStatus}</b></td><td>{status}</td></tr><tr><td><b>{lblIP}</b></td><td>{ip}</td></tr><tr><td><b>{lblMAC}</b></td><td>{mac}</td></tr></table>', {
						lblStatus: _( 'Status' ),
						status: label,
						lblIP: _( 'IP address' ),
						ip: item.ip[ 0 ],
						lblMAC: _( 'MAC address' ),
						mac: item.mac ? item.mac[ 0 ] : ''
					} );
					var tooltip = new Tooltip({
						label: label,
						connectId: [ widget.domNode ]
					});
					// destroy the tooltip when the widget is destroyed
					aspect.after(widget, 'destroy', function() { tooltip.destroy(); });

					return widget;
				} )
			}, {
				name: 'user',
				label: _('User')
			}];

			// generate the data grid
			this._grid = new Grid({
				// property that defines the widget's position in a dijit.layout.BorderContainer,
				// 'center' is its default value, so no need to specify it here explicitely
				multiActionsAlwaysActive: true,
				// region: 'center',
				actions: this._actionList(),
				columns: columns,
				cacheRowWidgets: false,
				moduleStore: new Memory(),
				footerFormatter: lang.hitch( this, function( nItems, nItemsTotal ) {
					var failed = 0;
					var msg = lang.replace( _( '{0} computers are in this room' ), [ nItemsTotal ] );

					if ( ! this._dataStore ) {
						return '';
					}
					this._dataStore.fetch( {
						query: '',
						onItem: lang.hitch( this, function( item ) {
							if ( item.connection[ 0 ] != 'connected' ) {
								failed += 1;
							}
						} )
					} );
					if ( failed ) {
						msg += ' ('+ lang.replace( _( '{0} powered off/misconfigured' ), [ failed ] ) + ')';
					}
					return msg;
				} )
			} );


			// add the grid to the title pane
			this._titlePane.addChild(this._grid);


			// // add search form to the title pane
			// this._titlePane.addChild(this._profileForm);

			var _container = new ContainerWidget( { region: 'top' } );
			this._profileInfo = new Text( {
				content: '<i>' + _( 'Determining active settings for the computer room ...' ) + '</i>',
				style: 'padding-bottom: 10px; padding-bottom; 10px; float: left;'
			} );
			this._validTo = new Text( {
				content: '&nbsp;',
				style: 'padding-bottom: 10px; padding-bottom; 10px; float: right;'
			} );

			_container.addChild( this._profileInfo );
			_container.addChild( this._validTo );
			this._titlePane.addChild( _container );
			//
			// conclusion
			//

			// we need to call page's startup method manually as all widgets have
			// been added to the page container object
			this._searchPage.startup();
			this._dataStore = new ItemFileWriteStore( { data : {
				identifier : 'id',
				label: 'name',
				items: []
			} } );
			this._objStore = new DataStore( { store : this._dataStore, idProperty: 'id' } );
			this._grid.moduleStore = this._objStore;
			this._grid._dataStore = this._dataStore;
			this._grid._grid.setStore( this._dataStore );
		},

		_actionList: function( demo ) {
			var actions = null;
			if ( demo === undefined ) {
				demo = this._demo.running;
			}

			actions = lang.clone( this._actions );
			if ( demo === false ) {
				actions.push( {
					name: 'ScreenLock',
					field: 'ScreenLock',
					label: lang.hitch(this, function(item) {
						if ( !item ) { // column title
							return '<span style="height: 0px; font-weight: normal; color: rgba(0,0,0,0);">' + _( 'unlock' ) + '</span>';
						}
						if ( !item.teacher || item.teacher[ 0 ] === false ) {
							if ( item.ScreenLock[0] === true ) {
								return _('unlock');
							} else if ( item.ScreenLock[0] === false ) {
								return _('lock');
							}
						} 
						return '';
					}),
					iconClass: lang.hitch( this, function( item ) {
						if ( !item ) {
							return null;
						}
						if ( item.ScreenLock[ 0 ] === null ) {
							return 'umcIconLoading';
						}
						return null;
					} ),
					isStandardAction: true,
					isMultiAction: false,
					canExecute: function( item ) {
						return item.connection[ 0 ] == 'connected' && item.user && item.user[ 0 ] && ( !item.teacher || item.teacher[ 0 ] === false );
					},
					callback: lang.hitch(this, function( ids, items ) {
						var comp = items[ 0 ];
						this.umcpCommand( 'computerroom/lock', { 
							computer: comp.id[ 0 ],
							device : 'screen',
							lock: comp.ScreenLock[ 0 ] !== true } );
						this._objStore.put( { id: comp.id[ 0 ], ScreenLock: null } );
					} )
				} );
				actions.push( {
					name: 'demoClientStop',
					label: lang.hitch( this, function( item ) {
						if ( !item || item.DemoServer[ 0 ] === true ) {
							return '';
						} else {
							return _( 'stop presentation' );
						}
					} ),
					isStandardAction: false,
					isMultiAction: false,
					isContextAction: true,
					canExecute: function( item ) {
						return item.connection[ 0 ] == 'connected' && item.DemoClient && item.DemoClient[ 0 ] === true;
					},
					callback: lang.hitch( this, function() {
						this.umcpCommand( 'computerroom/demo/stop', {} );
					} )
				} );
			} else {
				actions.push( {
					name: 'demoStop',
					label: lang.hitch( this, function( item ) {
						if ( !item ) {
							return _( 'presentation' );
						} else {
							return _( 'stop' );
						}
					} ),
					isStandardAction: true,
					isMultiAction: false,
					canExecute: function( item ) {
						return item.connection[ 0 ] == 'connected' && item.DemoServer && item.DemoServer[ 0 ] === true;
					},
					callback: lang.hitch( this, function() {
						this.umcpCommand( 'computerroom/demo/stop', {} );
					} )
				} );
			}

			return actions;
		},

		postCreate: function() {
			this.changeRoom();
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

				deferred = deferred.then(function () {
					// try to acquire the session
					okButton.set('disabled', true);
					return tools.umcpCommand('computerroom/room/acquire', {
						school: vals.school,
						room: vals.room
					});
				}).then(lang.hitch(this, function(response) {
					okButton.set('disabled', false);
					if ( response.result.success === false ) {
						// we could not acquire the room
						if ( response.result.message == 'ALREADY_LOCKED' ) {
							dialog.alert(_('Failed to open a new session for the room.'));
						} else if ( response.result.message == 'EMPTY_ROOM' ) {
							dialog.alert( _( 'The room is empty or the computers are not configured correctly. Please select another room.' ) );
						}
						return;
					}
					this._currentRoom = vals.room;
					this._currentSchool = vals.school;

					// reload the grid
					this.queryRoom();

					// update the header text containing the room
					this._updateHeader(vals.room);
					this._grid._updateFooterContent();

					// destroy the dialog
					_cleanup();
				}), function() {
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
				label: _( 'computer room' ),
				description: _( 'Choose the computer room to monitor' ),
				size: 'One',
				depends: 'school',
				dynamicValues: 'computerroom/rooms',
				onChange: lang.hitch(this, function(roomDN) {
					// display a warning in case the room is already taken
					var msg = '';
					var room = _getRoom(roomDN);
					if (room && room.locked) {
						msg = '<p>' + _('<b>Note:</b> This computer room is currently in use by %s.', room.user) + '</p>';
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
				'class' : 'umcPopup',
				style: 'max-width: 400px;'
			});
			_dialog.show();
			okButton.set('disabled', true);
		},

		queryRoom: function( reload ) {
			if ( this._updateTimer ) {
				window.clearTimeout( this._updateTimer );
			}
			this.umcpCommand( 'computerroom/query', {
				reload: reload !== undefined ? reload: false
			} ).then( lang.hitch( this, function( response ) {
				this._settingsDialog.update();
				array.forEach( response.result, function( item ) {
					this._objStore.put( item );
				}, this );
				this._updateTimer = window.setTimeout( lang.hitch( this, '_updateRoom', {} ), 2000 );
			} ) );
		},

		_updateRoom: function() {
			this.umcpCommand( 'computerroom/update' ).then( lang.hitch( this, function( response ) {
				var demo = false, demo_server = null, demo_user = null, demo_systems = 0;

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

				this._profileInfo.set( 'content', '<i>' + _( 'Determining active settings for the computer room ...' ) + '</i>' );
				array.forEach( response.result.computers, function( item ) {
					this._objStore.put( item );
				}, this );

				if ( response.result.computers.length ) {
					this._grid._updateFooterContent();
				}

				if ( response.result.settingEndsIn ) {
					var style = '';

					if ( response.result.settingEndsIn <= 5 ) {
						style = 'style="color: red"';
					}
					var labelValidTo = _( 'valid for' ) + lang.replace( ' <a href="javascript:void(0)" {style} onclick=\'dijit.byId("{id}").show()\'>' + _( '{time} minutes' ) + '</a>', {
						time: response.result.settingEndsIn,
						id: this._rescheduleDialog.id,
						style: style
					} );
					this._validTo.set( 'content', labelValidTo );
				} else {
					if ( this._validTo.get( 'content' ) != '&nbsp;' ) {
						this._validTo.set( 'content', '&nbsp;' );
						this._settingsDialog.update();
					}
				}

				var text = _( 'No user specific settings are defined for the computer room' );
				if ( this._settingsDialog.personalActive() ) {
					text = _( 'User specific settings for the computer room are active' );
				}
				var label = lang.replace( '{lblSettings} (<a href="javascript:void(0)" ' +
									  	  'onclick=\'dijit.byId("{id}").show()\'>{changeLabel}</a>)', {
										  	  lblSettings: text,
										  	  changeLabel: _( 'change' ),
										  	  id: this._settingsDialog.id
									  	  } );
				this._profileInfo.set( 'content', label );
				this._updateTimer = window.setTimeout( lang.hitch( this, '_updateRoom', {} ), 2000 );

				// update the grid actions
				this._dataStore.fetch( {
					query: '',
					onItem: lang.hitch( this, function( item ) {
						if ( item.DemoServer[ 0 ] === true ) {
							demo = true;
							demo_server = item.id[ 0 ];
							demo_user = item.user[ 0 ];
							demo_systems += 1;
						} else if ( item.DemoClient[ 0 ] === true ) {
							demo = true;
							demo_systems += 1;
						}
					} )
				} );
				if ( this._demo.running != demo || this._demo.server != demo_server ) {
					this._grid.set( 'actions', this._actionList( demo && demo_server !== null ), true );
				}
				this._demo = {
					running: demo,
					server: demo_server,
					user: demo_user,
					systems: demo_systems
				};

			} ) );
		}
	});

});
