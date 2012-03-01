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
/*global console dojo dojox dijit window umc */

dojo.provide("umc.modules.printermoderation");

dojo.require( "dojo.date" );
dojo.require( "dojo.date.locale" );

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.Grid");
dojo.require("umc.widgets.Module");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.SearchForm");
dojo.require("umc.widgets.ProgressInfo");

dojo.declare("umc.modules.printermoderation", [ umc.widgets.Module, umc.i18n.Mixin ], {
	// summary:
	//		Print job moderation
	// description:
	//		This module helps to control the print jobs of the pupils.

	// the property field that acts as unique identifier for the object
	idProperty: 'id',

	// internal reference to the grid
	_grid: null,

	// internal reference to the search page
	_searchPage: null,

	// widget for displaying the progress of an operation
	_progressInfo: null,

	postMixInProperties: function() {
		this.inherited(arguments);

		this.standbyOpacity = 1;
	},

	buildRendering: function() {
		this.inherited(arguments);

		// setup a progress bar with some info text
		this._progressInfo = new umc.widgets.ProgressInfo( {
			style: 'min-width: 400px;'
		} );

		// start the standby animation in order prevent any interaction before the
		// form values are loaded
		this.standby(true);

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
		var actions = [{
			name: 'view',
			label: this._( 'View' ),
			description: this._( 'View the print job.' ),
			isStandardAction: true,
			isMultiAction: true,
			callback: dojo.hitch( this, function( ids, items ) {
				dojo.forEach( items, dojo.hitch( this, function ( item ) {
					// document.location.host + '//' + document.location.host +
					var url = dojo.replace( '/umcp/command/printermoderation/download?username={0}&printjob={1}', [ item.username, item.filename ] );
					window.open( url );
				} ) );
			} )
		}, {
			name: 'print',
			label: this._( 'Print' ),
			description: this._( 'Print the document.' ),
			isStandardAction: true,
			isMultiAction: true,
			callback: dojo.hitch(this, '_printJobs')
		}, {
			name: 'delete',
			label: this._( 'Delete' ),
			description: this._( 'Delete the print job.' ),
			isStandardAction: true,
			isMultiAction: true,
			iconClass: 'umcIconDelete',
			callback: dojo.hitch(this, '_deletePrintJobs')
		}];

		// define the grid columns
		var columns = [{
			name: 'user',
			label: this._( 'User' ),
			width: '30%'
		}, {
			name: 'printjob',
			label: this._( 'Print job' ),
			width: '35%'
		}, {
			name: 'pages',
			label: this._( 'Pages' ),
			width: '8%'
		}, {
			name: 'date',
			label: this._( 'Date' ),
			width: '20%',
			formatter: dojo.hitch( this, function( key, rowIndex ) {
				return dojo.date.locale.format( new Date( key[ 0 ], key[ 1 ] - 1, key[ 2 ], key[ 3 ], key[ 4 ] ), { formatLength: 'short' } );
			} )
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			actions: actions,
			defaultAction: 'view',
			columns: columns,
			moduleStore: this.moduleStore,
			sortIndex: -4,
			// initial query
			query: { 'class' : 'None', pattern: '' }
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
			dynamicValues: 'printermoderation/schools'
		}, {
			type: 'ComboBox',
			name: 'class',
			description: this._('Select a class or workgroup.'),
			label: this._('Class or workroup'),
			size: 'TwoThirds',
			staticValues: [
				{ 'id' : 'None', 'label' : this._( 'All classes and workgroups' ) }
			],
			dynamicValues: 'printermoderation/groups',
			depends: 'school'
		}, {
			type: 'TextBox',
			name: 'pattern',
			value: '',
			description: this._('Specifies the substring pattern which is searched for in the first name, surname and username'),
			label: this._('Name')
		}];

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
			})
		});

		// turn off the standby animation as soon as all form values have been loaded
		this.connect(this._searchForm, 'onValuesInitialized', function() {
			this.standby(false);
		});

		// add search form to the title pane
		titlePane.addChild(this._searchForm);

		this._searchPage.startup();
	},

	_deletePrintJobs: function(ids, items) {
		umc.dialog.confirm( this._( 'Should the selected print jobs be deleted?' ), [ {
			label: this._( 'Delete' ),
			callback: dojo.hitch( this, function() {
				var finished_func = dojo.hitch( this, function() {
					this._progressInfo.update( items.length, this._( 'Finished' ) );
					this.moduleStore.onChange();
					this.standby( false );
				} );
				var deferred = new dojo.Deferred();

				this._progressInfo.set( 'maximum', items.length );
				this._progressInfo.update( 0, '', this._( 'Deleting print jobs ...' ) );
				this.standby( true, this._progressInfo );
				deferred.resolve();

				dojo.forEach( items, dojo.hitch( this, function( item, i ) {
					deferred = deferred.then( dojo.hitch( this, function() {
						this._progressInfo.update( i, dojo.replace( this._( 'Print job {0} from {1}' ), [ item.printjob, item.user ] ) );
						return this.umcpCommand( 'printermoderation/delete', {
							username: item.username,
							printjob: item.filename
						} );
					} ), finished_func );
				} ) );
				deferred.then( finished_func, finished_func );
			} )
		}, {
			label: this._( 'Cancel' ),
			'default': true
		} ] );
	},

	_printJobs: function(ids, items) {
		var dialog = null, form = null;

		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		var _print = dojo.hitch( this, function( printer ) {
			var deferred = new dojo.Deferred();
			var finished_func = dojo.hitch(this, function() {
				this.moduleStore.onChange();
				this._progressInfo.update( ids.length, this._( 'Finished' ) );
				this.standby( false );
			} );
			this._progressInfo.set( 'maximum', ids.length );
			this._progressInfo.updateTitle( this._( 'Printing ...' ) );
			this.standby( true, this._progressInfo );
			deferred.resolve();

			dojo.forEach( items, function( item, i ) {
				deferred = deferred.then( dojo.hitch( this, function() {
					this._progressInfo.update( i, dojo.replace( this._( 'Print job <i>{printjob}</i> of <i>{user}</i>' ), item ) );
					return umc.tools.umcpCommand( 'printermoderation/print', {
						username: item.username,
						printjob: item.filename,
						printer: printer
					} );
				} ) );
			}, this);

			// finish the progress bar and add error handler
			deferred = deferred.then( finished_func, finished_func );
		} );

		var message = '';
		if ( ids.length == 1 ) {
			message = dojo.replace( this._( 'A printer must be selected on which the document <i>{printjob}</i> should be printed.' ), items[ 0 ] );
		} else {
			message = dojo.replace( this._( 'A printer must be selected on which the {0} documents should be printed.' ), [ items.length ] );
		}
		message = '<p>' + message + '</p>';
		form = new umc.widgets.Form( {
			style: 'max-width: 500px;',
			widgets: [ {
				type: 'Text',
				name: 'info',
				content: message
			},{
				type: 'ComboBox',
				name: 'printer',
				dynamicValues: 'printermoderation/printers',
				label: this._( 'Printer' )
			} ],
			buttons: [ {
				name: 'submit',
				label: this._( 'Print' ),
				style: 'float: right;',
				callback: function() {
					var printer = form.getWidget( 'printer' );
					_cleanup();
					_print( printer.get( 'value' ) );
				}
			}, {
				name: 'cancel',
				label: this._( 'Cancel' ),
				callback: _cleanup
			}],
			layout: [ 'info', 'printer' ]
		});

		dialog = new dijit.Dialog( {
			title: this._( 'Print' ),
			content: form,
			'class': 'umcPopup'
		} );
		dialog.show();
	}
});



