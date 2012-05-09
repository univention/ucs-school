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

dojo.provide("umc.modules._computerroom.Reschedule");

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

dojo.declare("umc.modules._computerroom.RescheduleDialog", [ dijit.Dialog, umc.widgets.StandbyMixin, umc.i18n.Mixin ], {
	// summary:
	//		This class represents the screenshot view

	// internal reference to the flavored umcpCommand function
	umcpCommand: null,

	style: 'max-width: 300px',

	// use i18n information from umc.modules.schoolgroups
	i18nClass: 'umc.modules.computerroom',

	_form: null,

	rescheduleDialog: null,

	postMixInProperties: function() {
		this.inherited(arguments);
	},

	buildRendering: function() {
		this.inherited( arguments );
		// add remaining elements of the search form
		this.set( 'title', this._( 'Validity of personal settings' ) );

		var widgets = [ {
			type: 'Text',
			name: 'text',
			label: this._( 'Modify the time to define the new timestamp of validity for the personal settings.' )
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
				this.umcpCommand( 'computerroom/settings/reschedule', {
					period: this._form.getWidget( 'period' ).get( 'value' )
				} ).then( dojo.hitch( this, function( response ) {
					console.log( response );
					this.onPeriodChanged( this._form.getWidget( 'period' ).get( 'value' ) );
					this.hide();
				} ) );
			} )
		} , {
			name: 'cancel',
			label: this._( 'cancel' ),
			onClick: dojo.hitch( this, function() {
				this.hide();
				this.onClose();
			} )
		} ];

		// generate the search form
		this._form = new umc.widgets.Form({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			widgets: widgets,
			layout: [ 'text', 'period' ],
			buttons: buttons
		});

		this.set( 'content', this._form );
	},

	update: function( school, room ) {
		this.umcpCommand( 'computerroom/settings/get', {} ).then( dojo.hitch( this, function( response ) {
			umc.tools.forIn( response.result, function( key, value ) {
				this._form.getWidget( key ).set( 'value', value );
			}, this );
		} ) );
	},

	onClose: function() {
		// event stub
	},

	onPeriodChanged: function() {
		// event stub
	}
});




