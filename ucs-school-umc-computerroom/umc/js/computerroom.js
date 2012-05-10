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
/*global window console dojo dojox dijit umc */

dojo.provide("umc.modules.computerroom");

dojo.require("dijit.Dialog");
dojo.require("dojo.data.ItemFileWriteStore");
dojo.require("dojo.store.DataStore");
dojo.require("dojo.store.Memory");
dojo.require("dojox.math");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.TitlePane");
dojo.require("umc.widgets.Grid");
dojo.require("umc.widgets.Module");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.Form");
dojo.require("umc.widgets.ContainerWidget");

dojo.require("umc.modules._computerroom.ScreenshotView");
dojo.require("umc.modules._computerroom.Settings");
dojo.require("umc.modules._computerroom.Reschedule");

dojo.declare("umc.modules.computerroom", [ umc.widgets.Module, umc.i18n.Mixin ], {
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
			label: dojo.hitch(this, function(item) {
				if (!item) {
					header = !header;
					if ( header ) {
						return this._( 'Actions' );
					} else {
						return this._( 'watch' );
					}
				}
				return this._( 'watch' );
			}),
			isStandardAction: true,
			isMultiAction: true,
			description: function( item ) {
				return dojo.replace( '<div style="display: table-cell; vertical-align: middle; width: 240px;height: 200px;"><img id="screenshotTooltip-{0}" src="" style="width: 230px; display: block; margin-left: auto; margin-right: auto;"/></div>', item.id );
			},
			onShowDescription: function( target, item ) {
				var image = dojo.byId( 'screenshotTooltip-' + item.id[ 0 ] );
				image.src = '/umcp/command/computerroom/screenshot?computer=' + item.id[ 0 ] + '&random=' + Math.random();
			},
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected';
			},
			callback: dojo.hitch(this, function( ids, items ) {
				if ( items.length === 0 ) {
					items = this._grid.getAllItems();
				}
				this.selectChild( this._screenshotView );
				this._screenshotView.load( dojo.map( dojo.filter( items, function( item ) {
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
			label: this._('Logout user'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected' && item.user[ 0 ];
			},
			callback: dojo.hitch(this, function( ids, items ) {
				var comp = items[ 0 ];
				this.umcpCommand( 'computerroom/user/logout', { computer: comp.id[ 0 ] } );
			} )
		}, {
			name: 'computerShutdown',
			field: 'connection',
			label: this._('Shutdown computer'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected';
			},
			callback: dojo.hitch(this, function( ids, items ) {
				var comp = items[ 0 ];
				this.umcpCommand( 'computerroom/computer/state', { 
					computer: comp.id[ 0 ],
					state: 'poweroff'
				} );
			} )
		}, {
			name: 'computerStart',
			field: 'connection',
			label: this._('Switch on computer'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return ( item.connection[ 0 ] == 'error' || item.connection[ 0 ] == 'offline' ) && item.mac[ 0 ] !== null;
			},
			callback: dojo.hitch(this, function( ids, items ) {
				var comp = items[ 0 ];
				this.umcpCommand( 'computerroom/computer/state', { 
					computer: comp.id[ 0 ],
					state: 'poweron'
				} );
			} )
		}, {
			name: 'computerRestart',
			field: 'connection',
			label: this._('Restart computer'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected';
			},
			callback: dojo.hitch(this, function( ids, items ) {
				var comp = items[ 0 ];
				this.umcpCommand( 'computerroom/computer/state', { 
					computer: comp.id[ 0 ],
					state: 'restart'
				} );
			} )
		}, {
			name: 'lockInput',
			label: dojo.hitch( this, function( item ) {
				if ( !item ) {
					return '';
				}
				if ( item.InputLock ) {
					if ( item.InputLock[ 0 ] === true ) {
						return this._('Unlock input devices');
					} else if ( item.InputLock[ 0 ] === false ) {
						return this._('Lock input devices');
					}
				}
				return '';
			} ),
			iconClass: dojo.hitch( this, function( item ) {
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
			callback: dojo.hitch(this, function( ids, items ) {
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
			label: this._('Start presentation'),
			isStandardAction: false,
			isContextAction: true,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected' && item.user[ 0 ] && item.DemoServer[ 0 ] !== true;
			},
			callback: dojo.hitch( this, function( ids, items ) {
				this.umcpCommand( 'computerroom/demo/start', { server: items[ 0 ].id[ 0 ] } );
				umc.dialog.alert( this._( "The presentation is starting. This may take a few moments. When the presentation server is started a columns presentation is shown that contains a button 'stop' to end the presentation." ), this._( 'Presentation' ) );
			} )
		}, {
			name: 'reconnect',
			label: this._( 'Reinitialize monitoring' ),
			isStandardAction: false,
			isContextAction: true,
			isMultiAction: false,
			callback: dojo.hitch( this, function() { this.queryRoom( true ); } )
		} ];
	},

	buildRendering: function() {
		// is called after all DOM nodes have been setup
		// (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		this._rescheduleDialog = new umc.modules._computerroom.RescheduleDialog( {
			umcpCommand: dojo.hitch( this.umcpCommand )
		} );
		this._settingsDialog = new umc.modules._computerroom.SettingsDialog( {
			umcpCommand: dojo.hitch( this.umcpCommand )
		} );

		dojo.connect( this._rescheduleDialog, 'onPeriodChanged', dojo.hitch( this._settingsDialog, function( value ) {
			this._form.getWidget( 'period' ).set( 'value', value ) ;
		} ) );
		dojo.connect( this._settingsDialog, 'onPeriodChanged', dojo.hitch( this._rescheduleDialog, function( value ) {
			this._form.getWidget( 'period' ).set( 'value', value ) ;
		} ) );
		// render the page containing search form and grid
		this.renderSearchPage();

		this._screenshotView = new umc.modules._computerroom.ScreenshotView();
		this.addChild( this._screenshotView );
		dojo.connect( this._screenshotView, 'onClose', this, 'closeScreenView' );
	},

	closeScreenView: function() {
		this.selectChild( this._searchPage );
	},

	_updateHeader: function( room ) {
		if ( room ) {
			room = umc.tools.explodeDn( room, true )[ 0 ];
			room = room.replace( /^[^\-]+-/, '' );
		} else {
			room = this._('No room selected');
		}
		var label = dojo.replace('{roomLabel}: {room} ' +
				'(<a href="javascript:void(0)" ' +
				'onclick=\'dijit.byId("{id}").changeRoom()\'>{changeLabel}</a>)', {
			roomLabel: this._('Room'),
			room: room,
			changeLabel: this._('select room'),
			id: this.id
		});
		this._titlePane.set( 'title', label );
	},

	renderSearchPage: function(containers, superordinates) {
		// render all GUI elements for the search formular and the grid

		// render the search page
		this._searchPage = new umc.widgets.Page({
			headerText: this.description,
			helpText: this._( "Here you can watch the student's computers, locking the computers, show presentations, control the internet access and define the available printers and shares." )
		});

		// umc.widgets.Module is also a StackContainer instance that can hold
		// different pages (see also umc.widgets.TabbedModule)
		this.addChild(this._searchPage);

		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		this._titlePane = new umc.widgets.ExpandingTitlePane({
			title: this._('Room administration')
		});
		this._searchPage.addChild(this._titlePane);

		this._updateHeader();

		//
		// data grid
		//


		// define the grid columns
		var columns = [{
			name: 'name',
			label: this._('Name'),
			formatter: dojo.hitch( this, function( value, rowIndex ) {
				var item = this._grid._grid.getItem( rowIndex );
				var icon = 'offline';
				var label = this._( 'The computer is not running' );

				if ( item.connection[ 0 ] == 'connected' ) {
					icon = 'demo-offline';
					label = this._( 'Monitoring is activated' );
				} else if ( item.connection[ 0 ] == 'autherror' ) {
					label = this._( 'The monitoring mode has failed. It seems that the monitoring service is not configured properly.' );
				} else if ( item.connection[ 0 ] == 'error' ) {
					label = this._( 'The monitoring mode has failed. Maybe the service is not installed or the Firewall is active.' );
				}
				if ( item.DemoServer[ 0 ] === true ) {
					icon = 'demo-server';
					label = this._( 'The computer is showing a presentation currently' );
				} else if ( item.DemoClient[ 0 ] === true ) {
					icon = 'demo-client';
					label = this._( 'The computer is participating in a  presentation currently' );
				}
				var widget = umc.widgets.Text( {} );
				widget.set( 'content', dojo.replace( '<img src="images/icons/16x16/computerroom-{icon}.png" height="16" width="16" style="float:left; margin-right: 5px" /> {value}', {
					icon: icon,
					value: value
				} ) );
				label = dojo.replace( '<table><tr><td><b>{lblStatus}</b></td><td>{status}</td></tr><tr><td><b>{lblIP}</b></td><td>{ip}</td></tr><tr><td><b>{lblMAC}</b></td><td>{mac}</td></tr></table>', {
					lblStatus: this._( 'Status' ),
					status: label,
					lblIP: this._( 'IP address' ),
					ip: item.ip[ 0 ],
					lblMAC: this._( 'MAC address' ),
					mac: item.mac ? item.mac[ 0 ] : ''
				} );
				var tooltip = new umc.widgets.Tooltip( {
					label: label,
					connectId: [ widget.domNode ]
				});
				// destroy the tooltip when the widget is destroyed
				tooltip.connect( widget, 'destroy', 'destroy' );

				return widget;
			} )
		}, {
			name: 'user',
			label: this._('User')
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			// property that defines the widget's position in a dijit.layout.BorderContainer,
			// 'center' is its default value, so no need to specify it here explicitely
			multiActionsAlwaysActive: true,
			// region: 'center',
			actions: this._actionList(),
			columns: columns,
			moduleStore: new dojo.store.Memory(),
			footerFormatter: dojo.hitch( this, function( nItems, nItemsTotal ) {
				var failed = 0;
				var msg = dojo.replace( this._( '{0} computers are in this room' ), [ nItemsTotal ] );

				if ( ! this._dataStore ) {
					return '';
				}
				this._dataStore.fetch( {
					query: '',
					onItem: dojo.hitch( this, function( item ) {
						if ( item.connection[ 0 ] != 'connected' ) {
							failed += 1;
						}
					} )
				} );
				if ( failed ) {
					msg += ' ('+ dojo.replace( this._( '{0} powered off/misconfigured' ), [ failed ] ) + ')';
				}
				return msg;
			} )
		} );


		// add the grid to the title pane
		this._titlePane.addChild(this._grid);


		// // add search form to the title pane
		// this._titlePane.addChild(this._profileForm);

		var _container = new umc.widgets.ContainerWidget( { region: 'top' } );
		this._profileInfo = new umc.widgets.Text( {
			content: '<i>' + this._( 'Determining active settings for the room ...' ) + '</i>',
			style: 'padding-bottom: 10px; padding-bottom; 10px; float: left;'
		} );
		this._validTo = new umc.widgets.Text( {
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
		this._dataStore = new dojo.data.ItemFileWriteStore( { data : {
			identifier : 'id',
			label: 'name',
			items: []
		} } );
		this._objStore = new dojo.store.DataStore( { store : this._dataStore, idProperty: 'id' } );
		this._grid.moduleStore = this._objStore;
		this._grid._dataStore = this._dataStore;
		this._grid._grid.setStore( this._dataStore );
	},

	_actionList: function( demo ) {
		var actions = null;
		if ( demo === undefined ) {
			demo = this._demo.running;
		}

		actions = dojo.clone( this._actions );
		if ( demo === false ) {
			actions.push( {
				name: 'ScreenLock',
				field: 'ScreenLock',
				label: dojo.hitch(this, function(item) {
					if ( !item ) { // column title
						return '<span style="height: 0px; font-weight: normal; color: rgba(0,0,0,0);">' + this._( 'unlock' ) + '</span>';
					}
					if ( !item.teacher || item.teacher[ 0 ] === false ) {
						if ( item.ScreenLock[0] === true ) {
							return this._('unlock');
						} else if ( item.ScreenLock[0] === false ) {
							return this._('lock');
						}
					} 
					return '';
				}),
				iconClass: dojo.hitch( this, function( item ) {
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
				callback: dojo.hitch(this, function( ids, items ) {
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
				label: dojo.hitch( this, function( item ) {
					if ( !item || item.DemoServer[ 0 ] === true ) {
						return '';
					} else {
						return this._( 'stop presentation' );
					}
				} ),
				isStandardAction: false,
				isMultiAction: false,
				isContextAction: true,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected' && item.DemoClient && item.DemoClient[ 0 ] === true;
				},
				callback: dojo.hitch( this, function() {
					this.umcpCommand( 'computerroom/demo/stop', {} );
				} )
			} );
		} else {
			actions.push( {
				name: 'demoStop',
				label: dojo.hitch( this, function( item ) {
					if ( !item ) {
						return this._( 'presentation' );
					} else {
						return this._( 'stop' );
					}
				} ),
				isStandardAction: true,
				isMultiAction: false,
				canExecute: function( item ) {
					return item.connection[ 0 ] == 'connected' && item.DemoServer && item.DemoServer[ 0 ] === true;
				},
				callback: dojo.hitch( this, function() {
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
		var dialog = null, form = null, okButton = null;
		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		// helper function to get the current room
		var _getRoom = function(roomDN) {
			var room = null;
			dojo.forEach(form.getWidget('room').getAllItems(), function(iroom) {
				if (iroom.id == roomDN) {
					room = iroom;
					return false;
				}
			});
			return room;
		};

		// define the callback function
		var _callback = dojo.hitch(this, function(vals) {
			// default to a resolved deferred object
			var deferred = new dojo.Deferred();
			deferred.resolve();

			// show confirmation dialog if room is already locked
			var room = _getRoom(vals.room);
			if (room.locked) {
				deferred = 	umc.dialog.confirm(this._('This computer room is currently in use by %s. You can take control over the room, however, the current teacher will be prompted a notification and its session will be closed.', room.user), [{
					name: 'cancel',
					label: this._('Cancel'),
					'default': true
				}, {
					name: 'takeover',
					label: this._('Take over')
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
				return umc.tools.umcpCommand('computerroom/room/acquire', {
					school: vals.school,
					room: vals.room
				});
			}).then(dojo.hitch(this, function(response) {
				okButton.set('disabled', false);
				if ( response.result.success === false ) {
					// we could not acquire the room
					if ( response.result.message == 'ALREADY_LOCKED' ) {
						umc.dialog.alert(this._('Failed to open a new session for the room.'));
					} else if ( response.result.message == 'EMPTY_ROOM' ) {
						umc.dialog.alert( this._( 'The room is empty or the computers are not configured correctly. Please select another room.' ) );
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
			type: 'ComboBox',
			name: 'school',
			description: this._('Choose the school'),
			size: 'One',
			label: this._('School'),
			dynamicValues: 'computerroom/schools',
			autoHide: true
		}, {
			type: 'ComboBox',
			name: 'room',
			label: this._( 'computer room' ),
			description: this._( 'Choose the computer room to monitor' ),
			size: 'One',
			depends: 'school',
			dynamicValues: 'computerroom/rooms',
			onChange: dojo.hitch(this, function(roomDN) {
				// display a warning in case the room is already taken
				var msg = '';
				var room = _getRoom(roomDN);
				if (room && room.locked) {
					msg = '<p>' + this._('<b>Note:</b> This computer room is currently in use by %s.', room.user) + '</p>';
				}
				form.getWidget('message').set('content', msg);
			})
		}, {
			type: 'Text',
			name: 'message',
			'class': 'umcSize-One'
		}];

		// define buttons and callbacks
		var buttons = [{
			name: 'submit',
			label: this._('Select room'),
			style: 'float:right',
			callback: _callback
		}, {
			name: 'cancel',
			label: this._('Cancel'),
			callback: _cleanup
		}];

		// generate the search form
		form = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			widgets: widgets,
			layout: [ 'school', 'room', 'message' ],
			buttons: buttons
		});
		okButton = form.getButton('submit');

		// enable button when values are loaded
		var signal = dojo.connect(form, 'onValuesInitialized', function() {
			dojo.disconnect(signal);
			okButton.set('disabled', false);
		});

		// show the dialog
		dialog = new dijit.Dialog({
			title: this._('Select computer room'),
			content: form,
			'class' : 'umcPopup',
			style: 'max-width: 400px;'
		});
		dialog.show();
		okButton.set('disabled', true);
	},

	queryRoom: function( reload ) {
		if ( this._updateTimer ) {
			window.clearTimeout( this._updateTimer );
		}
		this.umcpCommand( 'computerroom/query', {
			reload: reload !== undefined ? reload: false
		} ).then( dojo.hitch( this, function( response ) {
			this._settingsDialog.update();
			dojo.forEach( response.result, function( item ) {
				this._objStore.put( item );
			}, this );
			this._updateTimer = window.setTimeout( dojo.hitch( this, '_updateRoom', {} ), 2000 );
		} ) );
	},

	_updateRoom: function() {
		this.umcpCommand( 'computerroom/update' ).then( dojo.hitch( this, function( response ) {
			var demo = false, demo_server = null, demo_user = null, demo_systems = 0;

			if (response.result.locked) {
				// somebody stole our session...
				// break the update loop, prompt a message and ask for choosing a new room
				umc.dialog.confirm(this._('Control over the computer room has been taken by "%s", your session has been closed. In case this behaviour was not intended, please contact the other user. You can regain control over the computer room, by choosing it from the list of rooms again.', response.result.user), [{
					name: 'ok',
					label: this._('Ok'),
					'default': true
				}]).then(dojo.hitch(this, function() {
					this.changeRoom();
				}));
				return;
			}

			this._profileInfo.set( 'content', '<i>' + this._( 'Determining active settings for the room ...' ) + '</i>' );
			dojo.forEach( response.result.computers, function( item ) {
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
				var labelValidTo = this._( 'valid for' ) + dojo.replace( ' <a href="javascript:void(0)" {style} onclick=\'dijit.byId("{id}").show()\'>' + this._( '{time} minutes' ) + '</a>', {
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

			var text = this._( 'No personal settings for printing, share and internet access defined' );
			if ( this._settingsDialog.personalActive() ) {
				text = this._( 'Personal settings are active' );
			}
			var label = dojo.replace( '{lblSettings} (<a href="javascript:void(0)" ' +
									  'onclick=\'dijit.byId("{id}").show()\'>{changeLabel}</a>)', {
										  lblSettings: text,
										  changeLabel: this._( 'change' ),
										  id: this._settingsDialog.id
									  } );
			this._profileInfo.set( 'content', label );
			this._updateTimer = window.setTimeout( dojo.hitch( this, '_updateRoom', {} ), 2000 );

			// update the grid actions
			this._dataStore.fetch( {
				query: '',
				onItem: dojo.hitch( this, function( item ) {
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



