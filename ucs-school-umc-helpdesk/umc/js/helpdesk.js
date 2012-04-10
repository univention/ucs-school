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

dojo.provide("umc.modules.helpdesk");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.ExpandingTitlePane");
dojo.require("umc.widgets.Grid");
dojo.require("umc.widgets.Module");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.SearchForm");

dojo.declare("umc.modules.helpdesk", [ umc.widgets.Module, umc.i18n.Mixin ], {
	// summary:
	//		Template module to ease the UMC module development.
	// description:
	//		This module is a template module in order to aid the development of
	//		new modules for Univention Management Console.

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

		// it is important to call the parent's buildRendering() method
		this.inherited(arguments);

		// start the standby animation in order prevent any interaction before the
		// form values are loaded
		this.standby(true);

		// render the page containing search form and grid
		this.umcpCommand( 'helpdesk/configuration' ).then( dojo.hitch( this, function( response ) {
			if ( response.result.recipient ) {
				this.renderPage( response.result.username, response.result.school );
				this.standby( false );
			} else {
				umc.dialog.alert( this._( 'The helpdesk module is not configured properly. The recipient email address is not set.' ) )
				var hdl = dojo.connect( umc.dialog._alertDialog, 'onConfirm', dojo.hitch( this, function() {
					dojo.disconnect( hdl );
					dojo.publish('/umc/tabs/close', [ this ] );
				} ) );
			}
		} ) );
	},

	renderPage: function( username, school ) {

		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		var titlePane = new umc.widgets.ExpandingTitlePane( {
			title: this._( 'Message to the helpdesk team' )
		} );

		//
		// form
		//

		// add remaining elements of the search form
		var widgets = [ {
			type: 'TextBox',
			name: 'username',
			label: this._('User name'),
			value: username,
			disabled: true
		}, {
			type: 'TextBox',
			name: 'school',
			label: this._('School'),
			value: school,
			disabled: true
		}, {
			type: 'ComboBox',
			name: 'category',
			label: this._( 'Category' ),
			dynamicValues: 'helpdesk/categories'
		}, {
			type: 'TextArea',
			name: 'message',
			style: 'height: 200px;',
			label: this._( 'Message' )
		} ];

		// the layout is an 2D array that defines the organization of the form elements...
		// here we arrange the form elements in one row and add the 'submit' button
		var layout = [
			'username',
			'school',
			'category',
			'message'
		];

		// generate the form
		this._form = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			region: 'top',
			widgets: widgets,
			layout: layout
		});

		// turn off the standby animation as soon as all form values have been loaded
		this.connect( this._form, 'onValuesInitialized', function() {
			this.standby( false );
		});

		// add form to the title pane
		titlePane.addChild(this._form);



		// submit changes
		var buttons = [ {
            name: 'submit',
            label: this._( 'Send' ),
            'default': true,
            callback: dojo.hitch( this, function() {
				var values = this._form.gatherFormValues();
				if ( values.message ) {
					this.onSubmit( this._form.gatherFormValues() );
				} else {
					umc.dialog.alert( this._( 'The required message is missing. Therefore, no report has been sent to the helpdesk team.' ) );
				}
            } )
        }, {
            name: 'close',
            label: this._('Close'),
            callback: dojo.hitch(this, function() {
				var values = this._form.gatherFormValues();
				if ( values.message ) {
					umc.dialog.confirm( this._( 'Should the UMC module be closed? All unsaved modification will be lost.' ), [ {
						label: this._( 'Close' ),
						callback: dojo.hitch( this, function() {
							dojo.publish('/umc/tabs/close', [ this ] );
						} )
					}, {
						label: this._( 'Cancel' ),
						'default': true
					} ] );
				} else {
					dojo.publish('/umc/tabs/close', [ this ] );
				}
            } )
        } ];

		this._page = new umc.widgets.Page({
			headerText: this.description,
			helpText: '',
			footerButtons: buttons
		});

		this.addChild(this._page);
		this._page.addChild( titlePane );
	},

	onSubmit: function( values ) {
		this.umcpCommand( 'helpdesk/send', values ).then( dojo.hitch( this, function ( response ) {
			if ( response.result ) {
				umc.dialog.alert( this._( 'The report has been sent to the helpdesk team' ) );
				this._form._widgets.message.set( 'value', '' );
			} else {
				umc.dialog.alert( this._( 'The message could not be send to the helpdesk team: ' ) + response.message );
			}
		} ) );
	}
});



