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
	_presentationWidget: null,
	_presentationText: '',

	// internal reference to the expanding title pane
	_titlePane: null,

	_metaInfo: null,

	_dataStore: null,
	_objStore: null,

	_updateTimer: null,

	_screenshotView: null,

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

		// Set the opacity for the standby animation to 100% in order to mask
		// GUI changes when the module is opened. Call this.standby(true|false)
		// to enabled/disable the animation.
		// this.standbyOpacity = 1;
	},

	buildRendering: function() {
		// is called after all DOM nodes have been setup
		// (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		// render the page containing search form and grid
		this.renderSearchPage();

		this._screenshotView = new umc.modules._computerroom.ScreenshotView();
		this.addChild( this._screenshotView );
		dojo.connect( this._screenshotView, 'onClose', this, 'closeScreenView' );

		this._presentationWidget = new umc.widgets.ContainerWidget( {
			style: 'max-width: 450px;'
		} );
		this._presentationText = new umc.widgets.Text( {
			content: this._( 'Currently a presentation is running.' )
		} );
		this._presentationWidget.addChild( this._presentationText );
		this._presentationWidget.addChild( new umc.widgets.Button( {
			label: this._( 'End presentation' ),
			onClick: dojo.hitch( this, '_endPresentation' ),
			style: 'float: right;'
		} ) );
	},

	closeScreenView: function() {
		this.selectChild( this._searchPage );
	},

	_updateHeader: function(room) {
		var label = dojo.replace('{roomLabel}: {room} ' +
				'(<a href="javascript:void(0)" ' +
				'onclick=\'dijit.byId("{id}").changeRoom()\'>{changeLabel}</a>)', {
			roomLabel: this._('Selected room'),
			room: room ? umc.tools.explodeDn(room, true)[0] : this._('No room selected'),
			changeLabel: this._('change room'),
			id: this.id
		});
		this._metaInfo.set('content', label);
	},

	renderSearchPage: function(containers, superordinates) {
		// render all GUI elements for the search formular and the grid

		// render the search page
		this._searchPage = new umc.widgets.Page({
			headerText: this.description,
			helpText: ''
		});

		// umc.widgets.Module is also a StackContainer instance that can hold
		// different pages (see also umc.widgets.TabbedModule)
		this.addChild(this._searchPage);

		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		this._titlePane = new umc.widgets.ExpandingTitlePane({
			title: this._('Room administration')
		});
		this._searchPage.addChild(this._titlePane);

		this._metaInfo = new umc.widgets.Text({
			region: 'top',
			style: 'padding-bottom: 10px;'
		});
		this._searchPage.addChild(this._metaInfo);
		this._updateHeader();

		//
		// data grid
		//

		// define grid actions
		var actions = [{
			name: 'screenshot',
			field: 'screenshot',
			label: dojo.hitch(this, function(item) {
				if (!item) {
					return this._('Screenshot');
				}
				return this._('Show');
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
				this.selectChild( this._screenshotView );
				this._screenshotView.load( dojo.map( items, function( item ) {
					return { 
						computer: item.id[ 0 ],
						username: item.user[ 0 ]
					};
				} ) );
			} )
		}, {
			name: 'ScreenLock',
			field: 'ScreenLock',
			label: dojo.hitch(this, function(item) {
				if ( !item ) { // column title
					return this._( 'Screen' );
				}
				if ( item.ScreenLock[0] === true ) {
					return this._('Unlock');
				} else if ( item.ScreenLock[0] === false ) {
					return this._('Lock');
				} else {
					return '';
				}
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
				return item.connection[ 0 ] == 'connected';
			},
			callback: dojo.hitch(this, function( ids, items ) {
				var comp = items[ 0 ];
				this.umcpCommand( 'computerroom/lock', { 
					computer: comp.id[ 0 ],
					device : 'screen',
					lock: comp.ScreenLock[ 0 ] !== true } );
				this._objStore.put( { id: comp.id[ 0 ], ScreenLock: null } );
			} )
		}, {
			name: 'logout',
			label: this._('Logout user'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected' && item.user[ 0 ];
			},
			callback: dojo.hitch(this, '_dummy')
		}, {
			name: 'computerShutdown',
			label: this._('Shutdown computer'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected';
			},
			callback: dojo.hitch(this, '_dummy')
		}, {
			name: 'computerStart',
			label: this._('Switch on computer'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'error';
			},
			callback: dojo.hitch(this, '_dummy')
		}, {
			name: 'computerRestart',
			label: this._('Restart computer'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected';
			},
			callback: dojo.hitch(this, '_dummy')
		}, {
			name: 'lockInput',
			label: this._('Lock input devices'),
			isStandardAction: false,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected' && item.user[ 0 ];
			},
			callback: dojo.hitch(this, '_dummy')
		}, {
			name: 'presentation',
			label: this._('Start presentation'),
			isStandardAction: false,
			isContextAction: true,
			isMultiAction: false,
			canExecute: function( item ) {
				return item.connection[ 0 ] == 'connected' && item.user[ 0 ];
			},
			callback: dojo.hitch( this, '_startPresentation' )
		}];

		// define the grid columns
		var columns = [{
			name: 'name',
			label: this._('Name')
		}, {
			name: 'user',
			label: this._('User')
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			// property that defines the widget's position in a dijit.layout.BorderContainer,
			// 'center' is its default value, so no need to specify it here explicitely
			// region: 'center',
			actions: actions,
			// defines which data fields are displayed in the grids columns
			columns: columns,
			moduleStore: new dojo.store.Memory()
		} );


		// add the grid to the title pane
		this._titlePane.addChild(this._grid);

		//
		// profile form
		//

		// add remaining elements of the search form
		var widgets = [{
			type: 'ComboBox',
			name: 'webProfile',
			label: this._('Active web access profile'),
			size: 'TwoThirds',
			staticValues: [ 'Wikipedia', 'Facebook' ]
		}, {
			type: 'ComboBox',
			name: 'sharesProfile',
			label: this._('Active shares'),
			size: 'TwoThirds',
			staticValues: [ 'All shares', 'Only class shares', 'no shares' ]
		}, {
			type: 'ComboBox',
			name: 'printer',
			label: this._('Print mode'),
			size: 'TwoThirds',
			staticValues: [
				this._('Printing deactivated'),
				this._('Moderated printing'),
				this._('Free printing')
			]
		}, {
			type: 'ComboBox',
			name: 'period',
			label: this._('Reservation until end of'),
			size: 'TwoThirds',
			staticValues: [
				this._('1st lesson'),
				this._('2nd lesson'),
				this._('3rd lesson'),
				this._('4th lesson'),
				this._('6th lesson')
			]
		}];

		var buttons = [{
			name: 'submit',
			style: 'display:none;'
		}];

		var layout = [
			[ 'webProfile', 'sharesProfile', 'printer', 'period', 'submit' ]
		];

		// generate the search form
		this._profileForm = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			region: 'top',
			widgets: widgets,
			layout: layout,
			buttons: buttons
		});

		// add search form to the title pane
		this._titlePane.addChild(this._profileForm);

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

	_startPresentation: function( ids, items ) {
		this.umcpCommand( 'computerroom/demo/start', { server: items[ 0 ].id[ 0 ] } );
		this._presentationText.set( 'content', dojo.replace( this._( 'Currently a presentation is running. The computer of {0} is shown to all others. Click the following button to end the presentation' ), items[ 0 ].user ) );
		this.standby( true, this._presentationWidget );
	},

	_endPresentation: function() {
		this.umcpCommand( 'computerroom/demo/stop', {} );
		this.standby( false );
	},

	postCreate: function() {
		this.changeRoom();
	},

	_dummy: function() {
		umc.dialog.alert(this._('Feature not yet implemented'));
	},

	changeRoom: function() {
		// define a cleanup function
		var dialog = null, form = null;
		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		// add remaining elements of the search form
		var widgets = [{
			type: 'ComboBox',
			name: 'school',
			description: this._('Choose the school'),
			label: this._('School'),
			dynamicValues: 'computerroom/schools',
			autoHide: true
		}, {
			type: 'ComboBox',
			name: 'room',
			label: this._('Selected room'),
			depends: 'school',
			dynamicValues: 'computerroom/rooms'
		}];

		// define buttons and callbacks
		var buttons = [{
			name: 'submit',
			label: this._('Change room'),
			style: 'float:right',
			callback: dojo.hitch(this, function(vals) {
				// reload the grid
				this.queryRoom( vals.school, vals.room );

				// update the header text containing the room
				this._updateHeader(vals.room);

				// destroy the dialog
				_cleanup();
			})
		}, {
			name: 'cancel',
			label: this._('Cancel'),
			callback: _cleanup
		}];

		// generate the search form
		form = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			widgets: widgets,
			layout: [ [ 'school', 'room' ] ],
			buttons: buttons
		});

		// show the dialog
		dialog = new dijit.Dialog({
			title: this._('Change room'),
			content: form,
			'class' : 'umcPopup',
			style: 'max-width: 400px;'
		});
		dialog.show();
	},

	queryRoom: function( school, room ) {
		this.umcpCommand( 'computerroom/query', {
			school: school,
			room: room
		} ).then( dojo.hitch( this, function( response ) {
			dojo.forEach( response.result, function( item ) {
				this._objStore.put( item );
				var idx = this._grid.getItemIndex( item.id );
				this._grid._grid.rowSelectCell.setDisabled( idx, item.connection != 'connected' );
			}, this );
			if ( this._updateTimer ) {
				window.clearTimeout( this._updateTimer );
			}
			this._updateTimer = window.setTimeout( dojo.hitch( this, '_updateRoom' ), 2000 );
		} ) );
	},

	_updateRoom: function() {
		this.umcpCommand( 'computerroom/update' ).then( dojo.hitch( this, function( response ) {
			this._grid.clearDisabledItems( false );
			dojo.forEach( response.result, function( item ) {
				// this._objStore.put( dojo.mixin( item, { screenshot: dojox.math.gaussian() } ) );
				this._objStore.put( item );
				if ( item.connection !== undefined ) {
					var idx = this._grid.getItemIndex( item.id );
					this._grid._grid.rowSelectCell.setDisabled( idx, item.connection != 'connected' );
				}
			}, this );
			this._updateTimer = window.setTimeout( dojo.hitch( this, '_updateRoom' ), 2000 );
		} ) );
	}
});



