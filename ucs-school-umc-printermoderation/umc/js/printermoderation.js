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
/*global define,window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/Deferred",
	"dojo/date/locale",
	"dojox/html/entities",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Dialog",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/SearchForm",
	"umc/widgets/SearchBox",
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/ProgressBar",
	"umc/i18n!umc/modules/printermoderation"
], function(declare, lang, array, Deferred, locale, entities, dialog, tools, Dialog, Grid,
            Module, Page, Form, SearchForm, SearchBox, Text, ComboBox, ProgressBar, _) {

	return declare("umc.modules.printermoderation", [ Module ], {
		// summary:
		//		Print job moderation
		// description:
		//		This module helps to control the print jobs of the students.

		idProperty: 'id',

		_grid: null,
		_searchPage: null,
		_progressBar: null,

		selectablePagesToLayoutMapping: {
			_searchPage: 'searchpage-grid'
		},

		buildRendering: function() {
			this.inherited(arguments);

			// setup a progress bar with some info text
			this._progressBar = new ProgressBar({
				style: 'min-width: 400px;'
			});
			this.own(this._progressBar);

			this._searchPage = new Page({
				fullWidth: true
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
						var url = lang.replace( '/univention/command/printermoderation/download?username={0}&printjob={1}', [encodeURIComponent(item.username), encodeURIComponent(item.filename)] );
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
				iconClass: 'trash',
				callback: lang.hitch(this, '_deletePrintJobs')
			}];

			var _array2Date = function(key) {
				 return new Date( key[ 0 ], key[ 1 ] - 1, key[ 2 ], key[ 3 ], key[ 4 ] );
			};

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
				formatter: lang.hitch( this, function(key) {
					return locale.format( _array2Date(key), { formatLength: 'short' } );
				}),
				sortFormatter: _array2Date
			}];

			this._grid = new Grid({
				actions: actions,
				defaultAction: 'view',
				hideContextActionsWhenNoSelection: false,
				columns: columns,
				moduleStore: this.moduleStore,
				sortIndex: -4
			});

			this._searchPage.addChild(this._grid);

			var widgets = [{
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
				name: 'school',
				description: _('Select the school.'),
				label: _( 'School' ),
				autoHide: true,
				size: 'TwoThirds',
				dynamicValues: 'printermoderation/schools'
			}, {
				type: ComboBox,
				'class': 'umcTextBoxOnBody',
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
				type: SearchBox,
				'class': 'umcTextBoxOnBody',
				name: 'pattern',
				size: 'TwoThirds',
				inlineLabel: _('Search...'),
				value: '',
				description: _('Specifies the substring pattern which is searched for in the first name, surname and username'),
				label: _('Name'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];

			var layout = [
				[ 'school', 'class', 'pattern' ]
			];

			this._searchForm = new SearchForm({
				region: 'nav',
				hideSubmitButton: true,
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
		},

		_deletePrintJobs: function(ids, items) {
			dialog.confirm(_( 'Should the selected print jobs be deleted?' ), [{
				label: _('Cancel'),
				'default': true
			}, {
				label: _('Delete'),
				callback: lang.hitch(this, function() {
					var finished_func = lang.hitch(this, function() {
						this._progressBar.setInfo(null, _('Finished'), 100);
						this.moduleStore.onChange();
						this.standby(false);
					} );
					var deferred = new Deferred();

					this._progressBar.setInfo(_( 'Deleting print jobs ...' ), '', 0);
					this.standby(true, this._progressBar);
					deferred.resolve();

					array.forEach(items, lang.hitch(this, function(item, i) {
						deferred = deferred.then(lang.hitch(this, function() {
							this._progressBar.setInfo(null, lang.replace(_('Print job {0} from {1}'), [item.printjob, item.user]), (i / ids.length) * 100);
							return this.umcpCommand('printermoderation/delete', {
								username: item.username,
								printjob: item.filename
							});
						}), finished_func);
					}));
					deferred.then(finished_func, finished_func);
				})
			}]);
		},

		_printJobs: function(ids, items) {
			var _dialog = null, form = null;

			var _cleanup = function() {
				_dialog.close();
			};

			var _print = lang.hitch( this, function( printer ) {
				var deferred = new Deferred();
				var finished_func = lang.hitch(this, function() {
					this.moduleStore.onChange();
					this._progressBar.setInfo( null, _( 'Finished' ), 100 );
					this.standby( false );
				} );
				this._progressBar.setInfo( _( 'Printing ...' ) );
				this.standby( true, this._progressBar );
				deferred.resolve();

				array.forEach( items, function( item, i ) {
					deferred = deferred.then( lang.hitch( this, function() {
						this._progressBar.setInfo( null, lang.replace( _( 'Print job <i>{printjob}</i> of <i>{user}</i>' ), item ), (i / ids.length) * 100 );
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
			if (ids.length === 1) {
				var printjob = '<i>' + entities.encode(items[0].printjob) + '</i>';
				message = entities.encode(_('A printer must be selected on which the document {0} should be printed.'));
				message = lang.replace(message, [printjob]);
			} else {
				message = entities.encode(lang.replace(_('A printer must be selected on which the {0} documents should be printed.'), [items.length]));
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
					name: 'school',
					label: _('School'),
					autoHide: true,
					value: this._searchForm.getWidget('school').get('value'),
					dynamicValues: 'printermoderation/schools'
				},{
					type: ComboBox,
					name: 'printer',
					dynamicValues: 'printermoderation/printers',
					depends: 'school',
					label: _('Printer')
				} ],
				buttons: [ {
					name: 'cancel',
					label: _( 'Cancel' ),
					align: 'left',
					callback: _cleanup
				}, {
					name: 'submit',
					label: _( 'Print' ),
					callback: function() {
						var printer = form.getWidget( 'printer' );
						_cleanup();
						_print( printer.get( 'value' ) );
					}
				}],
				layout: [ 'info', 'school', 'printer' ]
			});

			_dialog = new Dialog( {
				title: _( 'Print' ),
				content: form,
				destroyOnCancel: true
			} );
			_dialog.show();
		}
	});

});
