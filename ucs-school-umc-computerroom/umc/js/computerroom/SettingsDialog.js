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
/*global define dijit*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dijit/Dialog",
	"umc/tools",
	"umc/widgets/Form",
	"umc/widgets/ComboBox",
	"umc/widgets/TimeBox",
	"umc/widgets/TextArea",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/computerroom"
], function(declare, lang, Dialog, tools, Form, ComboBox, TimeBox, TextArea, StandbyMixin, _) {

	return declare("umc.modules.computerroom.SettingsDialog", [ Dialog, StandbyMixin ], {
		// summary:
		//		This class represents the screenshot view

		// internal reference to the flavored umcpCommand function
		umcpCommand: null,

		// indicates that computerroom is opened in exam mode
		exam: null,

		_form: null,

		postMixInProperties: function() {
			this.inherited(arguments);
		},

		buildRendering: function() {
			this.inherited( arguments );
			// add remaining elements of the search form
			this.set( 'title', _( 'Personal settings for the computer room' ) );

			var myRules = _( 'Personal internet rules' );
			var widgets = [ {
				type: ComboBox,
				name: 'internetRule',
				label: _('Web access profile'),
				sizeClass: 'One',
				dynamicValues: 'computerroom/internetrules',
				staticValues: [ { id: 'none', label: _( 'Default (global settings)' ) },
								{ id: 'custom', label: myRules } ],
				onChange: lang.hitch( this, function( value ) {
					this._form.getWidget( 'customRule' ).set( 'disabled', value != 'custom' );
				} )
			}, {
				type: TextArea,
				name: 'customRule',
				label: lang.replace( _( 'List of allowed web sites for "{myRules}"' ), {
					myRules: myRules
				} ),
				sizeClass: 'One',
				description: _( '<p>In this text box you can list web sites that are allowed to be used by the students. Each line should contain one web site. Example: </p><p style="font-family: monospace">univention.com<br/>wikipedia.org<br/></p>' ),
				validate: lang.hitch( this, function() {
					return !( this._form.getWidget( 'internetRule' ).get( 'value' ) == 'custom' && ! this._form.getWidget( 'customRule' ).get( 'value' ) );
				} ),
				onFocus: lang.hitch( this, function() {
					dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode ); // FIXME
				} ),
				disabled: true
			}, {
				type: ComboBox,
				name: 'shareMode',
				sizeClass: 'One',
				label: _('Share access'),
				description: _( 'Defines restriction for the share access' ),
				staticValues: [
					{ id: 'home', label: _('Home directory only') },
					{ id: 'all', label: _('Default (no restrictions)' ) }
				]
			}, {
				type: ComboBox,
				name: 'printMode',
				sizeClass: 'One',
				label: _('Print mode'),
				staticValues: [
					{ id: 'default', label: _( 'Default (global settings)' ) },
					{ id: 'none', label: _('Printing deactivated') },
					{ id: 'all', label: _('Free printing' ) }
				]
			}, {
				type: TimeBox,
				name: 'period',
				label: _('Valid until')
			}];

			var buttons = [ {
				name: 'submit',
				label: _( 'Set' ),
				style: 'float: right',
				onClick: lang.hitch( this, function() {
					var customRule = this._form.getWidget( 'customRule' );
					if ( ! customRule.validate() ) {
						dijit.showTooltip( _( '<b>At least one web site is required!</b>' ) + '<br/>' + customRule.description, customRule.domNode ); // FIXME
						return;
					}
					dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode ); // FIXME
					this.hide();
					this.save();
				} )
			} , {
				name: 'reset_to_default',
				label: _( 'Reset' ),
				style: 'float: right',
				onClick: lang.hitch( this, 'reset' )
			} , {
				name: 'cancel',
				label: _( 'Cancel' ),
				onClick: lang.hitch( this, function() {
					dijit.hideTooltip( this._form.getWidget( 'customRule' ).domNode );
					this.hide();
					this.update();
					this.onClose();
				} )
			} ];

			// generate the search form
			this._form = new Form({
				// property that defines the widget's position in a dijit.layout.BorderContainer
				widgets: widgets,
				layout: [ 'period', 'internetRule', 'customRule', 'shareMode', 'printMode' ],
				buttons: buttons
			});

			this.set( 'content', this._form );

			// hide time period on exam mode
			this.watch('exam', lang.hitch(this, function(name, old, value) {
				this._form.getWidget('period').set('visible', !value);
			}));
		},

		show: function() {
			this.standby(true);
			this.update().then(
				lang.hitch(this, 'standby', false),
				lang.hitch(this, 'standby', false)
			);
			this.inherited(arguments);
		},

		update: function() {
			// load settings and update form
			return this.umcpCommand('computerroom/settings/get', {}).then(lang.hitch(this, function(response) {
				tools.forIn(response.result, function(key, value) {
					var widget = this._form.getWidget(key);
					if (widget.setInitialValue) {
						widget.setInitialValue(value);
					} else {
						widget.set('value', value);
					}
				}, this);
			}));
		},

		reset: function() {
			this._form.getWidget( 'internetRule' ).set( 'value', 'none' );
			this._form.getWidget( 'printMode' ).set( 'value', 'default' );
			this._form.getWidget( 'shareMode' ).set( 'value', 'all' );
		},

		save: function() {
			// save settings
			var values = this._form.get('value');
			values.exam = this.exam || null;
			this.umcpCommand( 'computerroom/settings/set', values);
		},

		personalActive: function() {
			var values = this._form.get('value');
			return values.internetRule != 'none' || values.shareMode != 'all' || values.printMode != 'default';
		},

		onClose: function() {
			// event stub
		}

	});

});
