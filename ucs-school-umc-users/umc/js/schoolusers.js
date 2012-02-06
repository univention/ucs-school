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
dojo.require("umc.widgets.SearchForm");

// dojo.require("umc.modules._schoolusers.DetailPage");

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
	// _detailPage: null,
	_progressBar: null,
	_progressContainer: null,

	uninitialize: function() {
		this.inherited(arguments);

		this._progressContainer.destroyRecursive();
	},

	postMixInProperties: function() {
		// is called after all inherited properties/methods have been mixed
		// into the object (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		// Set the opacity for the standby animation to 100% in order to mask
		// GUI changes when the module is opened. Call this.standby(true|false)
		// to enabled/disable the animation.
		this.standbyOpacity = 1;
	},

	buildRendering: function() {
		// is called after all DOM nodes have been setup
		// (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		// start the standby animation in order prevent any interaction before the
		// form values are loaded
		this.standby(true);

		// render the page containing search form and grid
		this.renderSearchPage();
	},

	renderSearchPage: function(containers, superordinates) {
		// render all GUI elements for the search formular and the grid

		// setup search page and its main widgets
		// for the styling, we need a title pane surrounding search form and grid
		this._searchPage = new umc.widgets.Page({
			headerText: this.description,
			helpText: ''
		});

		// umc.widgets.Module is also a StackContainer instance that can hold
		// different pages (see also umc.widgets.TabbedModule)
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
			name: 'expires',
			label: this._('Password expiration date'),
			width: '40%'
		}];

		// generate the data grid
		this._grid = new umc.widgets.Grid({
			// property that defines the widget's position in a dijit.layout.BorderContainer,
			// 'center' is its default value, so no need to specify it here explicitely
			// region: 'center',
			actions: actions,
			// defines which data fields are displayed in the grids columns
			columns: columns,
			// a generic UMCP module store object is automatically provided
			// as this.moduleStore (see also umc.store.getModuleStore())
			moduleStore: this.moduleStore
			// initial query
			// query: { colors: 'None', name: '' }
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
			size: 'twoThirds',
			dynamicValues: 'schoolusers/schools'
		}, {
			type: 'ComboBox',
			name: 'class',
			description: this._('Select the class.'),
			label: this._('Class'),
			size: 'twoThirds',
			staticValues: [
				{ 'id' : 'None', 'label' : this._( 'All classes' ) }
			],
			dynamicValues: 'schoolusers/classes',
			depends: 'school'
		}, {
			type: 'TextBox',
			name: 'pattern',
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
			})
		});

		// turn off the standby animation as soon as all form values have been loaded
		this.connect(this._searchForm, 'onValuesInitialized', function() {
			this.standby(false);
		});

		// add search form to the title pane
		titlePane.addChild(this._searchForm);

		// setup a progress bar with some info text
		this._progressContainer = new umc.widgets.ContainerWidget({});
		this._progressBar = new dijit.ProgressBar({
			style: 'background-color: #fff;'
		});
		this._progressContainer.addChild(this._progressBar);
		this._progressContainer.addChild(new umc.widgets.Text({
			content: this._('Please wait, your requests are being processed...')
		}));


		//
		// conclusion
		//

		// we need to call page's startup method manually as all widgets have
		// been added to the page container object
		this._searchPage.startup();

		// // create a DetailPage instance
		// this._detailPage = new umc.modules._schoolusers.DetailPage({
		// 	moduleStore: this.moduleStore
		// });
		// this.addChild(this._detailPage);

		// // connect to the onClose event of the detail page... we need to manage
		// // visibility of sub pages here
		// // ... this.connect() will destroy signal handlers upon widget
		// // destruction automatically
		// this.connect(this._detailPage, 'onClose', function() {
		// 	this.selectChild(this._searchPage);
		// });
	},

	_resetPasswords: function( ids ) {
		var dialog = null, form = null;

		var _cleanup = function() {
			dialog.hide();
			dialog.destroyRecursive();
			form.destroyRecursive();
		};

		var _set_passwords = dojo.hitch( this, function( password, nextLogin ) {
			dojo.forEach(ids, function(iid, i) {
				var deferred = new dojo.Deferred();
				deferred.resolve();

				deferred = deferred.then( dojo.hitch( this, function() {
					this.updateProgress(i, ids.length );
					return umc.tools.umcpCommand( 'schoolusers/password/reset', {
						userDN: iid,
						newPassword: passwordWidget.get( 'value' )
					} );
				} ) );
			}, this);

			// finish the progress bar and add error handler
			deferred = deferred.then( dojo.hitch(this, function() {
				this.moduleStore.onChange();
				this.updateProgress( ids.length, ids.length );
			} ), dojo.hitch(this, function( error ) {
				this.moduleStore.onChange();
				this.updateProgress( ids.length, ids.length );
			} ) );
		} );

		form = new umc.widgets.Form({
			style: 'max-width: 500px;',
			widgets: [ {
				type: 'Text',
				name: 'info',
				content: this._( 'Reset passwords ...' )
			},{
				type: 'CheckBox',
				name: 'changeOnNextLogin',
				value: true,
				label: this._( 'user has to change password on next login' )
			}, {
				name: 'newPassword',
				type: 'PasswordBox',
				required: true,
				label: this._( 'New password' )
			} ],
			buttons: [ {
				name: 'submit',
				label: this._( 'Set' ),
				style: 'float: right;',
				callback: function() {
					var passwordWidget = form.getWidget( 'newPassword' );
					var nextLoginWidget = form.getWidget( 'changeOnNextLogin' );

					var password = passwordWidget.get( 'value' );
					var nextLogin = nextLoginWidget.get( 'value' );
					_cleanup();
					_set_passwords( password, nextLogin );
				}
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
	},

	updateProgress: function(i, n) {
		var progress = this._progressBar;
		if (i === 0) {
			// initiate the progressbar and start the standby
			progress.set('maximum', n);
			progress.set('value', 0);
			this.standby(true, this._progressContainer);
		}
		else if (i >= n || i < 0) {
			// finish the progress bar
			progress.set('value', n);
			this.standby(false);
		}
		else {
			progress.set('value', i);
		}
	}
});



