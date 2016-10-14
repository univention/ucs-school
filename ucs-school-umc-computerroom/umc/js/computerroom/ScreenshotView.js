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
/*global define console window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/aspect",
	"dojo/dom",
	"dojo/dom-geometry",
	"dojox/html/entities",
	"dijit/layout/ContentPane",
	"dijit/_Contained",
	"dijit/Tooltip",
	"umc/widgets/ComboBox",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Button",
	"umc/widgets/Page",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/computerroom"
], function(declare, lang, array, aspect, dom, geometry, entities, ContentPane, _Contained, Tooltip, ComboBox, ContainerWidget, Button, Page, StandbyMixin, _) {

	// README: This is an alternative view
	// var Item = declare( "umc.modules.computerroom.Item", [ dijit.TitlePane, _Contained ], {

	// 	// the computer to show
	// 	computer: '',

	// 	// current user at the computer
	// 	username: '',

	// 	// image object
	// 	image: null,

	// 	// random extension to the URL to avoid caching
	// 	random: null,

	// 	// pattern for the image URI
	// 	_pattern: '/umcp/command/computerroom/screenshot?computer={computer}&random={random}',

	// 	// tiemr to update the iamges
	// 	_timer: null,

	// 	uninitialize: function() {
	// 		this.inherited( arguments );
	// 		if ( this._timer !== null ) {
	// 			window.clearTimeout( this._timer );
	// 		}
	// 	},

	// 	postMixInProperties: function() {
	// 		this.inherited( arguments );
	// 	},

	// 	_createURI: function() {
	// 		this.random = Math.random();
	// 		return lang.replace( this._pattern, this );
	// 	},

	// 	_updateImage: function() {
	// 		var img = dom.byId( lang.replace( 'screenshot-{computer}', this ) );
	// 		if ( !img ) {
	// 			img = new Image( 500 );
	// 			img.id = lang.replace( 'screenshot-{computer}', this );
	// 			img.src = this._createURI();
	// 			try {
	// 				this.set( 'content', img );
	// 			} catch ( error ) {
	// 				// ignore
	// 			}
	// 		} else {
	// 			img.src = this._createURI();
	// 		}

	// 		this._timer = window.setTimeout( lang.hitch( this, '_updateImage' ), 5000 );
	// 		return img;
	// 	},

	// 	buildRendering: function() {
	// 		this.inherited( arguments );

	// 		lang.mixin( this, {
	// 			title: lang.replace( _( '{username} at {computer}' ), this ),
	// 			description: this.username,
	// 			open: true,
	// 			content: this._updateImage()
	// 		} );
	// 		this.startup();
	// 	}
	// } );

	var Item = declare( "umc.modules.computerroom.Item", [ ContentPane, _Contained ], {

		// the computer to show
		computer: '',

		// current user at the computer
		username: '',

		// image object
		image: null,

		// random extension to the URL to avoid caching
		random: null,

		style: 'float: left; padding: 8px; position: relative;',

		// pattern for the image URI
		_pattern: '/umcp/command/computerroom/screenshot?computer={computer}&random={random}',

		// tiemr to update the iamges
		_timer: null,

		_currentURI: null,

		// default size (width) of the image
		defaultWidth: 250,

		uninitialize: function() {
			this.inherited( arguments );
			if ( this._timer !== null ) {
				window.clearTimeout( this._timer );
			}
		},

		_createURI: function() {
			this.random = Math.random();
			return lang.replace( this._pattern, this );
		},

		_updateImage: function( size ) {
			var img = dom.byId( lang.replace( 'img-{computer}', this ) );
			var em = dom.byId( lang.replace( 'em-{computer}', this ) );
			var tooltip = dom.byId( lang.replace( 'screenshotTooltip-{computer}', this ) );

			if ( size === undefined ) {
				size = this.defaultSize;
			} else {
				this.defaultSize = size;
			}

			if ( this.domNode ) {
				if ( size !== undefined ) {
					geometry.setContentSize( this.domNode, { w: size, h:size * 0.9 } );
				}
			}
			if ( em ) {
				em.innerHTML = this.username;
			}
			if ( img ) {
				var new_uri = this._createURI();
				img.src = new_uri;
				this._currentURI = new_uri;
			}
			if ( this._timer ) {
				window.clearTimeout( this._timer );
			}
			this._timer = window.setTimeout( lang.hitch( this, function() { this._updateImage(); } ), 5000 );
		},

		buildRendering: function() {
			this.inherited( arguments );

			lang.mixin( this, {
				content: lang.replace('<em style="font-style: normal; font-size: 80%; padding: 4px; border: 1px solid #000; color: #000; background: #fff; display: block;position: absolute; top: 14px; left: 0px;" id="em-{computer}"></em><img style="width: 100%;" id="img-{computer}" alt="{alternative}"></img>', {
					computer: entities.encode(this.computer),
					width: this.defaultSize,
					alternative: entities.encode(_('Currently there is no screenshot available. Wait a few seconds.'))
				})
			} );
			this.startup();

			// use dijit.Tooltip here to not hide screenshot tooltips if set up in user preferences
			var tooltip = new Tooltip({
				'class': 'umcTooltip',
				label: lang.replace('<div style="display: table-cell; vertical-align: middle; width: 440px;height: 400px;"><img alt="{1}" id="screenshotTooltip-{0}" src="" style="width: 430px; display: block; margin-left: auto; margin-right: auto;"/></div>', [
					entities.encode(this.computer),
					entities.encode(_('Currently there is no screenshot available. Wait a few seconds.'))
				]),
				connectId: [ this.domNode ],
				onShow: lang.hitch( this, function() {
					var image = dom.byId( 'screenshotTooltip-' + this.computer );
					if ( image ) {
						image.src = this._currentURI ? this._currentURI: this._createURI();
					}
				} )
			});

			// destroy the tooltip when this widget is destroyed
			aspect.after(this, 'destroy', function() { tooltip.destroy(); });

			this._timer = window.setTimeout( lang.hitch( this, function() { this._updateImage(); } ), 500 );
		}
	} );

	return declare("umc.modules.computerroom.ScreenshotView", [ Page, StandbyMixin ], {
		// summary:
		//		This class represents the screenshot view

		// internal reference to the flavored umcpCommand function
		umcpCommand: null,

		_container: null,

		_cbxSize: null,

		postMixInProperties: function() {
			this.inherited(arguments);

			// set the page header
			this.headerText = _( 'Screenshots of computers' );
			this.helpText = _( 'This page shows screenshots of selected computers that will be updated continuously.' );

		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			this.inherited(arguments);

			var footer = new ContainerWidget( {
				'class': 'umcPageFooter',
				region: 'bottom'
			} );
			footer.addChild( new Button( {
				label: _( 'Back to overview' ),
				style: 'float: left',
				onClick: lang.hitch( this, function() {
					this._cleanup();
					this.onClose();
				} )
			} ) );
			this.addChild( footer );

			var header = new ContainerWidget( {
				'class': 'umcPageHeader',
				region: 'top'
			} );
			this._cbxSize = new ComboBox( {
				name: _( 'Size' ),
				style: 'float: left',
				staticValues: [
					{ id: 200, label: _( 'Tiny' ) },
					{ id: 250, label: _( 'Small' ) },
					{ id: 350, label: _( 'Normal' ) },
					{ id: 500, label: _( 'Large' ) }
				],
				value: 250,
				onChange: lang.hitch( this, function( newValue ) {
					console.log( 'ComboBox.onChange: ' + newValue );
					if ( this._container.hasChildren() ) {
						array.forEach( this._container.getChildren(), lang.hitch( this, function( child ) {
							child._updateImage( newValue );
						} ) );
					}
				} )
			} );
			header.addChild( this._cbxSize );
			this.addChild( header );

			this._container = new ContainerWidget({
					scrollable: true
			});
			this.addChild( this._container );
			this.startup();
		},

		_cleanup: function() {
			if ( this._container.hasChildren() ) {
				array.forEach( this._container.getChildren(), lang.hitch( this, function( child ) {
					this._container.removeChild( child );
					child.destroyRecursive();
				} ) );
			}
		},

		load: function( ids ) {
			// during loading show the standby animation
			this.standby(true);
			this._cleanup();
			array.forEach( ids, lang.hitch( this, function( item ) {
				var computer = new Item( lang.mixin( item, {
					defaultSize: this._cbxSize.get( 'value' )
				} ) );
				this._container.addChild( computer );
			} ) );
			this.startup();
			this.standby(false);
		},

		onClose: function() {
			// event stub
		}
	});

});
