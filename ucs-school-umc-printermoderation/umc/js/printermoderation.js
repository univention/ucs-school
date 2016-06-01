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
/*global define window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/Deferred",
	"dijit/Dialog",
	"dojo/date/locale",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/SearchForm",
	"umc/widgets/TextBox",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/ProgressInfo",
	"umc/i18n!umc/modules/printermoderation"
], function(declare, lang, array, Deferred, Dialog, locale, dialog, tools, Grid,
            Module, Page, Form, SearchForm, TextBox, Text, ComboBox, ProgressInfo, _) {

	return declare("umc.modules.printermoderation", [ Module ], {
		// summary:
		//		Print job moderation
		// description:
		//		This module helps to control the print jobs of the students.

		idProperty: 'id',

		_grid: null,
		_searchPage: null,
		_progressInfo: null,
		standbyOpacity: 1,

		buildRendering: function() {
			this.inherited(arguments);

			// setup a progress bar with some info text
			this._progressInfo = new ProgressInfo({
				style: 'min-width: 400px;'
			});
			this.own(this._progressInfo);

			this._searchPage = new Page({
				headerText: this.description,
				helpText: ''
			});

			// define grid actions
			var actions = [{
				name: 'view',
				label: _( 'View' ),
				description: _( 'View the print job.' ),
				isStandardAction: true,
				isMultiAction: true,
				callback: lang.hitch( this, function( ids, items ) {
					array.forEach( items, lang.hitch( this, function ( item ) {
						// document.location.host + '//' + document.location.host +
						var url = lang.replace( '/univention-management-console/command/printermoderation/download?username={0}&printjob={1}', [ item.username, item.filename ] );
						window.open( url );
					} ) );
				} )
			}, {
				name: 'print',
				label: _( 'Print' ),
				description: _( 'Print the document.' ),
				isStandardAction: true,
				isMultiAction: true,
				callback: lang.hitch(this, '_printJobs')
			}, {
				name: 'delete',
				label: _( 'Delete' ),
				description: _( 'Delete the print job.' ),
				isStandardAction: true,
				isMultiAction: true,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_deletePrintJobs')
			}];

			// define the grid columns
			var columns = [{
				name: 'user',
				label: _( 'User' ),
				width: '30%'
			}, {
				name: 'printjob',
				label: _( 'Print job' ),
				width: '35%'
			}, {
				name: 'pages',
				label: _( 'Pages' ),
				width: '8%'
			}, {
				name: 'date',
				label: _( 'Date' ),
				width: '20%',
				formatter: lang.hitch( this, function( key, rowIndex ) {
					return locale.format( new Date( key[ 0 ], key[ 1 ] - 1, key[ 2 ], key[ 3 ], key[ 4 ] ), { formatLength: 'short' } );
				} )
			}];

			this._grid = new Grid({
				actions: actions,
				defaultAction: 'view',
				columns: columns,
				moduleStore: this.moduleStore,
				sortIndex: -4
			});

			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				description: _('Select the school.'),
				label: _( 'School' ),
				autoHide: true,
				size: 'TwoThirds',
				dynamicValues: 'printermoderation/schools'
			}, {
				type: ComboBox,
				name: 'class',
				description: _('Select a class or workgroup.'),
				label: _('Class or workroup'),
				size: 'TwoThirds',
				staticValues: [
					{ 'id' : 'None', 'label' : _( 'All classes and workgroups' ) }
				],
				dynamicValues: 'printermoderation/groups',
				depends: 'school'
			}, {
				type: TextBox,
				name: 'pattern',
				value: '',
				description: _('Specifies the substring pattern which is searched for in the first name, surname and username'),
				label: _('Name')
			}];

			var layout = [
				[ 'school', 'class', 'pattern', 'submit' ]
			];

			this._searchForm = new SearchForm({
				region: 'nav',
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					this._grid.filter(values);
				})
			});
			this.standbyDuring(this._searchForm.ready()).then(lang.hitch(this, function() {
				this._grid.filter(this._searchForm.get('value'));
			}));

			this._searchPage.addChild(this._searchForm);
			this.addChild(this._searchPage);
			this._searchPage.startup();
		},

		_deletePrintJobs: function(ids, items) {
			dialog.confirm( _( 'Should the selected print jobs be deleted?' ), [ {
				label: _( 'Delete' ),
				callback: lang.hitch( this, function() {
					var finished_func = lang.hitch( this, function() {
						this._progressInfo.update( items.length, _( 'Finished' ) );
						this.moduleStore.onChange();
						this.standby( false );
					} );
					var deferred = new Deferred();

					this._progressInfo.set( 'maximum', items.length );
					this._progressInfo.update( 0, '', _( 'Deleting print jobs ...' ) );
					this.standby( true, this._progressInfo );
					deferred.resolve();

					array.forEach( items, lang.hitch( this, function( item, i ) {
						deferred = deferred.then( lang.hitch( this, function() {
							this._progressInfo.update( i, lang.replace( _( 'Print job {0} from {1}' ), [ item.printjob, item.user ] ) );
							return this.umcpCommand( 'printermoderation/delete', {
								username: item.username,
								printjob: item.filename
							} );
						} ), finished_func );
					} ) );
					deferred.then( finished_func, finished_func );
				} )
			}, {
				label: _( 'Cancel' ),
				'default': true
			} ] );
		},

		_printJobs: function(ids, items) {
			var _dialog = null, form = null;

			var _cleanup = function() {
				_dialog.hide();
				_dialog.destroyRecursive();
				form.destroyRecursive();
			};

			var _print = lang.hitch( this, function( printer ) {
				var deferred = new Deferred();
				var finished_func = lang.hitch(this, function() {
					this.moduleStore.onChange();
					this._progressInfo.update( ids.length, _( 'Finished' ) );
					this.standby( false );
				} );
				this._progressInfo.set( 'maximum', ids.length );
				this._progressInfo.updateTitle( _( 'Printing ...' ) );
				this.standby( true, this._progressInfo );
				deferred.resolve();

				array.forEach( items, function( item, i ) {
					deferred = deferred.then( lang.hitch( this, function() {
						this._progressInfo.update( i, lang.replace( _( 'Print job <i>{printjob}</i> of <i>{user}</i>' ), item ) );
						return tools.umcpCommand( 'printermoderation/print', {
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
				message = lang.replace( _( 'A printer must be selected on which the document <i>{printjob}</i> should be printed.' ), items[ 0 ] );
			} else {
				message = lang.replace( _( 'A printer must be selected on which the {0} documents should be printed.' ), [ items.length ] );
			}
			message = '<p>' + message + '</p>';
			form = new Form( {
				style: 'max-width: 500px;',
				widgets: [ {
					type: Text,
					name: 'info',
					content: message
				},{
					type: ComboBox,
					name: 'printer',
					dynamicValues: 'printermoderation/printers',
					label: _( 'Printer' )
				} ],
				buttons: [ {
					name: 'submit',
					label: _( 'Print' ),
					style: 'float: right;',
					callback: function() {
						var printer = form.getWidget( 'printer' );
						_cleanup();
						_print( printer.get( 'value' ) );
					}
				}, {
					name: 'cancel',
					label: _( 'Cancel' ),
					callback: _cleanup
				}],
				layout: [ 'info', 'printer' ]
			});

			_dialog = new Dialog( {
				title: _( 'Print' ),
				content: form,
				'class': 'umcPopup'
			} );
			_dialog.show();
		}
	});

});
