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
/*global define console*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/tools",
	"umc/widgets/Form",
	"umc/widgets/Text",
	"umc/widgets/TimeBox",
	"umc/widgets/StandbyMixin",
	"dijit/Dialog",
	"umc/i18n!/umc/modules/computerroom"
], function(declare, lang, tools, Form, Text, TimeBox, StandbyMixin, Dialog, _) {

	return declare("umc.modules.computerroom.RescheduleDialog", [ Dialog, StandbyMixin ], {
		// summary:
		//		This class represents the screenshot view

		// internal reference to the flavored umcpCommand function
		umcpCommand: null,

		style: 'max-width: 300px',

		_form: null,

		rescheduleDialog: null,

		postMixInProperties: function() {
			this.inherited(arguments);
		},

		buildRendering: function() {
			this.inherited( arguments );
			// add remaining elements of the search form
			this.set( 'title', _( 'Validity of personal settings' ) );

			var widgets = [ {
				type: Text,
				name: 'text',
				label: _( 'Modify the time to define the new timestamp of validity for the personal settings.' )
			}, {
				type: TimeBox,
				name: 'period',
				label: _('Valid to')
			}];

			var buttons = [ {
				name: 'submit',
				label: _( 'Set' ),
				style: 'float: right',
				onClick: lang.hitch( this, function() {
					this.umcpCommand( 'computerroom/settings/reschedule', {
						period: this._form.getWidget( 'period' ).get( 'value' )
					} ).then( lang.hitch( this, function( response ) {
						console.log( response );
						this.onPeriodChanged( this._form.getWidget( 'period' ).get( 'value' ) );
						this.hide();
					} ) );
				} )
			} , {
				name: 'cancel',
				label: _( 'cancel' ),
				onClick: lang.hitch( this, function() {
					this.hide();
					this.onClose();
				} )
			} ];

			// generate the search form
			this._form = new Form({
				// property that defines the widget's position in a dijit.layout.BorderContainer
				widgets: widgets,
				layout: [ 'text', 'period' ],
				buttons: buttons
			});

			this.set( 'content', this._form );
		},

		update: function( school, room ) {
			this.umcpCommand( 'computerroom/settings/get', {} ).then( lang.hitch( this, function( response ) {
				tools.forIn( response.result, function( key, value ) {
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
});
