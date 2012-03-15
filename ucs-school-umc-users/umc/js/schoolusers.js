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
/*global console dojo dojox dijit umc */

dojo.provide("umc.modules.schoolusers");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.Grid");
dojo.require("umc.widgets.Module");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.ProgressInfo");
dojo.require("umc.widgets.SearchForm");

dojo.declare("umc.modules.schoolusers", [ umc.widgets.Module, umc.i18n.Mixin ], {
	// summary:
	//		Template module to ease the UMC module development.
	// description:
	//		This module is a template module in order to aid the development of
	//		new modules for Univention Management Console.

	// the property field that acts as unique identifier for the object
	idProperty: 'id',

	// internal reference to the grid
	_grid: null,

	// internal reference to the search page
	_searchPage: null,

	// internal reference to the detail page for editing an object
	_progressInfo: null,

	uninitialize: function() {
		this.inherited(arguments);

		this._progressInfo.destroyRecursive();
	},

	buildRendering: function() {
		this.inherited(arguments);

		// activate standby mode
		this.standbyOpacity = 1;
		this.standby( true );


		// render the page containing search form and grid
		this.renderSearchPage();
	},

	renderSearchPage: function(containers, superordinates) {
		// render all GUI elements for the search formular and the grid

		this._searchPage = new umc.widgets.Page({
			headerText: this.description,
			helpText: ''
		});

		this.addChild(this._searchPage);

		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		var titlePane = new umc.widgets.ExpandingTitlePane({
			title: this._('Search results')
		});
		this._searchPage.addChild(titlePane);


		//
		// data grid
		//

		// define grid actions
		var actions = [ {
			name: 'reset',
			label: this._( 'Reset password' ),
			description: this._( 'Resets password of user.' ),
			isStandardAction: true,
			isMultiAction: true,
			callback: dojo.hitch( this, '_resetPasswords' )
		}];

		// define the grid columns
		var columns = [{
			name: 'name',
			label: this._('Name'),
			width: '60%'
		}, {
			name: 'passwordexpiry',
			label: this._('Password expiration date'),
			width: '40%',
			'formatter': function( key ) {
				if ( key ) {
					var date = dojo.date.locale.parse( key, { datePattern : 'yyyy-MM-dd', selector: 'date' } );
					if ( date ) {
						return dojo.date.locale.format( date, { selector: 'date' } );
					}
				}
				return '-';
			}
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			actions: actions,
			columns: columns,
			moduleStore: this.moduleStore,
			// initial query
			query: { 'class': 'None', pattern: '' }
		});

		// add the grid to the title pane
		titlePane.addChild(this._grid);


		//
		// search form
		//

		// add remaining elements of the search form
		var widgets = [{
			type: 'ComboBox',
			name: 'school',
			description: this._('Select the school.'),
			label: this._( 'School' ),
			autoHide: true,
			size: 'TwoThirds',
			umcpCommand: dojo.hitch( this, 'umcpCommand' ),
			dynamicValues: 'schoolusers/schools'
		}, {
			type: 'ComboBox',
			name: 'class',
			description: this._('Select a class or workgroup.'),
			label: this._( 'Class or workgroup' ),
			staticValues: [
				{ 'id' : 'None', 'label' : this._( 'All classes and workgroups' ) }
			],
			dynamicValues: 'schoolusers/groups',
			umcpCommand: dojo.hitch( this, 'umcpCommand' ),
			depends: 'school'
		}, {
			type: 'TextBox',
			name: 'pattern',
			size: 'TwoThirds',
			value: '',
			description: this._('Specifies the substring pattern which is searched for in the first name, surname and username'),
			label: this._('Name')
		}];

		// the layout is an 2D array that defines the organization of the form elements...
		// here we arrange the form elements in one row and add the 'submit' button
		var layout = [
			[ 'school', 'class', 'pattern', 'submit' ]
		];

		// generate the search form
		this._searchForm = new umc.widgets.SearchForm({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			region: 'top',
			widgets: widgets,
			layout: layout,
			onSearch: dojo.hitch(this, function(values) {
				// call the grid's filter function
				// (could be also done via dojo.connect() and dojo.disconnect() )
				this._grid.filter(values);
			}),
			onValuesInitialized: dojo.hitch( this, function() {
				// deactivate standby mode
				this.standby( false );
				// transparent standby mode
				this.standbyOpacity = 0.75;
			 } )
		});

		// add search form to the title pane
		titlePane.addChild(this._searchForm);

		// setup a progress bar with some info text
		this._progressInfo = new umc.widgets.ProgressInfo( {
			style: 'min-width: 400px'
		} );

		this._searchPage.startup();
	},

	_resetPasswords: function( ids, items ) {
		var dialog = null, form = null;

		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		var errors = [];
		var finished_func = dojo.hitch( this, function() {
			this.moduleStore.onChange();
			this._progressInfo.update( ids.length, this._( 'Finished' ) );
			this.standby( false );
			if ( errors.length ) {
				var message = this._( 'Failed to reset the password for the following users:' ) + '<br><ul>';
				var _content = new umc.widgets.ContainerWidget( {
					scrollable: true,
					style: 'max-height: 500px'
				} );
				dojo.forEach( errors, function( item ) {
					message += '<li>' + item.name + '<br>' + item.message + '</li>';
				} );
				message += '</ul>';
				_content.addChild( new umc.widgets.Text( { content: message } ) );
				umc.dialog.alert( _content );
			}
		} );

		var _set_passwords = dojo.hitch( this, function( password, nextLogin ) {
			var deferred = new dojo.Deferred();

			this._progressInfo.set( 'maximum', ids.length );
			this._progressInfo.updateTitle( this._( 'Setting passwords' ) );
			deferred.resolve();
			this.standby( true, this._progressInfo );

			dojo.forEach( items, function( item, i ) {
				deferred = deferred.then( dojo.hitch( this, function() {
					this._progressInfo.update( i, this._( 'User: ' ) + item.name );
					return this.umcpCommand( 'schoolusers/password/reset', {
						userDN: item.id,
						newPassword: password,
						nextLogin: nextLogin
					} ).then( function( response ) {
						if ( dojo.isString( response.result ) ) {
							errors.push( { name: item.name, message: response.result } );
						}
					} );
				} ) );
			}, this );

			// finish the progress bar and add error handler
			deferred = deferred.then( finished_func, finished_func );
		} );

		form = new umc.widgets.Form({
			style: 'max-width: 500px;',
			widgets: [ {
				type: 'Text',
				name: 'info',
				content: '<p>' + dojo.replace( this._( 'Clicking the <i>Reset</i> button will set the password for all {0} selected students to the given password. For security reasons the students should be forced to change the passwort on the next login.' ), [ items.length ] ) + '</p>'
			},{
				type: 'CheckBox',
				name: 'changeOnNextLogin',
				value: true,
				label: this._( 'user has to change password on next login' )
			}, {
				name: 'newPassword',
				type: 'TextBox',
				required: true,
				label: this._( 'New password' )
			} ],
			buttons: [ {
				name: 'submit',
				label: this._( 'Reset' ),
				style: 'float: right;',
				callback: dojo.hitch( this, function() {
					var nextLoginWidget = form.getWidget( 'changeOnNextLogin' );
					var passwordWidget = form.getWidget( 'newPassword' );

					if ( ! form.validate() ) {
						passwordWidget.focus();
						return;
					}

					var password = passwordWidget.get( 'value' );
					var nextLogin = nextLoginWidget.get( 'value' );
					_cleanup();
					_set_passwords( password, nextLogin );
				} )
			}, {
				name: 'cancel',
				label: this._('Cancel'),
				callback: _cleanup
			}],
			layout: [ 'info', 'changeOnNextLogin', 'newPassword' ]
		});

		dialog = new dijit.Dialog( {
			title: this._( 'Reset passwords' ),
			content: form,
			'class': 'umcPopup'
		} );
		dialog.show();
	}
});



