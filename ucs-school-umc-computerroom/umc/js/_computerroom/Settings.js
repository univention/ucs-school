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
/*global console MyError dojo dojox dijit umc window Image */

dojo.provide("umc.modules._computerroom.Settings");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.Button");
dojo.require("umc.widgets.Form");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.Text");
dojo.require("umc.widgets.TimeBox");
dojo.require("umc.widgets.StandbyMixin");
dojo.require("umc.widgets.ContainerWidget");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.Dialog");

dojo.declare("umc.modules._computerroom.SettingsDialog", [ dijit.Dialog, umc.widgets.StandbyMixin, umc.i18n.Mixin ], {
	// summary:
	//		This class represents the screenshot view

	// internal reference to the flavored umcpCommand function
	umcpCommand: null,

	// use i18n information from umc.modules.schoolgroups
	i18nClass: 'umc.modules.computerroom',

	_form: null,

	postMixInProperties: function() {
		this.inherited(arguments);
	},

	buildRendering: function() {
		this.inherited( arguments );
		// add remaining elements of the search form
		this.set( 'title', this._( 'Personal settings for the computer room' ) );

		var myRules = this._( 'Personal internet rules' );
		var widgets = [ {
			type: 'ComboBox',
			name: 'internetRule',
			label: this._('Web access profile'),
			sizeClass: 'One',
			dynamicValues: 'computerroom/internetrules',
			staticValues: [ { id: 'none', label: this._( 'Default (global settings)' ) },
							{ id: 'custom', label: myRules } ],
			onChange: dojo.hitch( this, function( value ) {
				this._form.getWidget( 'customRule' ).set( 'disabled', value != 'custom' );
			} )
		}, {
			type: 'TextArea',
			name: 'customRule',
			label: dojo.replace( this._( 'List of allowed web sites for "{myRules}"' ), {
				myRules: myRules
			} ),
			sizeClass: 'One',
			description: this._( '<p>In this text box you can list web sites that are allowed to be used by the students. Each line should contain one web site. Example: </p><p style="font-family: monospace">univention.com</br>wikipedia.org</br></p>' ),
			validate: dojo.hitch( this, function() {
				return !( this._form.getWidget( 'internetRule' ).get( 'value' ) == 'custom' && ! this._form.getWidget( 'customRule' ).get( 'value' ) );
			} ),
			onFocus: dojo.hitch( this, function() {
				dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode );
			} ),
			disabled: true
		}, {
			type: 'ComboBox',
			name: 'shareMode',
			sizeClass: 'One',
			label: this._('share access'),
			description: this._( 'Defines restriction for the share access' ),
			staticValues: [
				{ id : 'none', label: this._( 'no access' ) },
				{ id: 'home', label : this._('home directory only') },
				{ id: 'all', label : this._('Default (no restrictions)' ) }
			]
		}, {
			type: 'ComboBox',
			name: 'printMode',
			sizeClass: 'One',
			label: this._('Print mode'),
			staticValues: [
				{ id : 'default', label: this._( 'Default (global settings)' ) },
				{ id: 'none', label : this._('Printing deactivated') },
				{ id: 'all', label : this._('Free printing' ) }
			]
		}, {
			type: 'TimeBox',
			name: 'period',
			label: this._('Valid to')
		}];

		var buttons = [ {
			name: 'submit',
			label: this._( 'Set' ),
			style: 'float: right',
			onClick: dojo.hitch( this, function() {
				var customRule = this._form.getWidget( 'customRule' );
				if ( ! customRule.validate() ) {
					dijit.showTooltip( this._( '<b>At least one web site is required!</b>' ) + '<br/>' + customRule.description, customRule.domNode );
					return;
				}
				dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode );
				this.hide();
				this.umcpCommand( 'computerroom/settings/set', {
					internetRule: this._form.getWidget( 'internetRule' ).get( 'value' ),
					customRule: this._form.getWidget( 'customRule' ).get( 'value' ),
					printMode: this._form.getWidget( 'printMode' ).get( 'value' ),
					shareMode: this._form.getWidget( 'shareMode' ).get( 'value' ),
					period: this._form.getWidget( 'period' ).get( 'value' )
				} ).then( dojo.hitch( this, function( response ) {
					this.onPeriodChanged( this._form.getWidget( 'period' ).get( 'value' ) );
					// this.rescheduleDialog.set( 'period', this._form.getWidget( 'period' ).get( 'value' ) );
				} ) );
			} )
		} , {
			name: 'reset_to_default',
			label: this._( 'reset' ),
			style: 'float: right',
			onClick: dojo.hitch( this, function() {
				this._form.getWidget( 'internetRule' ).set( 'value', 'none' );
				this._form.getWidget( 'printMode' ).set( 'value', 'default' );
				this._form.getWidget( 'shareMode' ).set( 'value', 'all' );
			} )
		} , {
			name: 'cancel',
			label: this._( 'cancel' ),
			onClick: dojo.hitch( this, function() {
				dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode );
				this.hide();
				this.onClose();
			} )
		} ];

		// generate the search form
		this._form = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			widgets: widgets,
			layout: [ 'internetRule', 'customRule', 'shareMode', 'printMode', 'period' ],
			buttons: buttons
		});

		this.set( 'content', this._form );
	},

	update: function( school, room ) {
		this.umcpCommand( 'computerroom/settings/get', {} ).then( dojo.hitch( this, function( response ) {
			umc.tools.forIn( response.result, function( key, value ) {
				this._form.getWidget( key ).set( 'value', value );
			}, this );
			this.onPeriodChanged( this._form.getWidget( 'period' ).get( 'value' ) );
			// this.rescheduleDialog.set( 'period', this._form.getWidget( 'period' ).get( 'value' ) );
		} ) );
	},

	personalActive: function() {
		return this._form.getWidget( 'internetRule' ).get( 'value' ) != 'none' || this._form.getWidget( 'shareMode' ).get( 'value' ) != 'all' || this._form.getWidget( 'printMode' ).get( 'value' ) != 'default';
	},

	onClose: function() {
		// event stub
	},

	onPeriodChanged: function() {
		// event stub
	}
});




