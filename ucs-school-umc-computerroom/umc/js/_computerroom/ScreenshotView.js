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

dojo.provide("umc.modules._computerroom.ScreenshotView");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.Button");
dojo.require("umc.widgets.Form");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.StandbyMixin");
dojo.require("umc.widgets.ContainerWidget");
dojo.require("dijit.layout.ContentPane");
dojo.require("dijit.TitlePane");

// README: This is an alternative view
// dojo.declare( "umc.modules._computerroom.Item", [ dijit.TitlePane, dijit._Contained, umc.i18n.Mixin ], {
// 	// use i18n information from umc.modules.schoolgroups
// 	i18nClass: 'umc.modules.computerroom',

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
// 		return dojo.replace( this._pattern, this );
// 	},

// 	_updateImage: function() {
// 		var img = dojo.byId( dojo.replace( 'screenshot-{computer}', this ) );
// 		if ( !img ) {
// 			img = new Image( 500 );
// 			img.id = dojo.replace( 'screenshot-{computer}', this );
// 			img.src = this._createURI();
// 			try {
// 				this.set( 'content', img );
// 			} catch ( error ) {
// 				// ignore
// 			}
// 		} else {
// 			img.src = this._createURI();
// 		}

// 		this._timer = window.setTimeout( dojo.hitch( this, '_updateImage' ), 5000 );
// 		return img;
// 	},

// 	buildRendering: function() {
// 		this.inherited( arguments );

// 		dojo.mixin( this, {
// 			title: dojo.replace( this._( '{username} at {computer}' ), this ),
// 			description: this.username,
// 			open: true,
// 			content: this._updateImage()
// 		} );
// 		this.startup();
// 	}
// } );

dojo.declare( "umc.modules._computerroom.Item", [ dijit.layout.ContentPane, dijit._Contained, umc.i18n.Mixin ], {
	// use i18n information from umc.modules.schoolgroups
	i18nClass: 'umc.modules.computerroom',

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
		return dojo.replace( this._pattern, this );
	},

	_updateImage: function( size ) {
		var img = dojo.byId( dojo.replace( 'img-{computer}', this ) );
		var em = dojo.byId( dojo.replace( 'em-{computer}', this ) );
		var tooltip = dojo.byId( dojo.replace( 'screenshotTooltip-{computer}', this ) );

		if ( size === undefined ) {
			size = this.defaultSize;
		} else {
			this.defaultSize = size;
		}

		if ( this.domNode ) {
			if ( size !== undefined ) {
				dojo.contentBox( this.domNode, { w: size, h:size * 0.9 } );
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
		this._timer = window.setTimeout( dojo.hitch( this, function() { this._updateImage() } ), 5000 );
	},

	buildRendering: function() {
		this.inherited( arguments );

		dojo.mixin( this, {
			content: dojo.replace( '<em style="font-style: normal; font-size: 80%; padding: 4px; border: 1px solid #000; color: #000; background: #fff; display: block;position: absolute; top: 14px; left: 0px;" id="em-{computer}"></em><img style="width: 100%;" id="img-{computer}"></img>', {
				computer: this.computer,
				width: this.defaultSize
			} )
		} );
		this.startup();

		var tooltip = new umc.widgets.Tooltip({
			label: dojo.replace( '<div style="display: table-cell; vertical-align: middle; width: 440px;height: 400px;"><img id="screenshotTooltip-{0}" src="" style="width: 430px; display: block; margin-left: auto; margin-right: auto;"/></div>', [ this.computer ] ),
			connectId: [ this.domNode ],
			onShow: dojo.hitch( this, function() {
				var image = dojo.byId( 'screenshotTooltip-' + this.computer );
				if ( image ) {
					image.src = this._currentURI ? this._currentURI: this._createURI();
				}
			} )
		});

		// destroy the tooltip when the widget is destroyed
		tooltip.connect( this, 'destroy', 'destroy' );

		this._timer = window.setTimeout( dojo.hitch( this, function() { this._updateImage() } ), 500 );
	}
} );

dojo.declare("umc.modules._computerroom.ScreenshotView", [ umc.widgets.Page, umc.widgets.StandbyMixin, umc.i18n.Mixin ], {
	// summary:
	//		This class represents the screenshot view

	// internal reference to the flavored umcpCommand function
	umcpCommand: null,

	// use i18n information from umc.modules.schoolgroups
	i18nClass: 'umc.modules.computerroom',

	_container: null,

	_cbxSize: null,

	postMixInProperties: function() {
		this.inherited(arguments);

		// set the page header
		this.headerText = this._( 'Screenshots of computers' );
		this.helpText = this._( 'This page shows screenshots of selected computers that will be updated every few seconds.' );

	},

	buildRendering: function() {
		// is called after all DOM nodes have been setup
		// (originates from dijit._Widget)

		this.inherited(arguments);

		var footer = new umc.widgets.ContainerWidget( {
			'class': 'umcPageFooter',
			region: 'bottom'
		} );
		footer.addChild( new umc.widgets.Button( {
			label: this._( 'back to overview' ),
			style: 'float: left',
			onClick: dojo.hitch( this, function() {
				this._cleanup();
				this.onClose();
			} )
		} ) );
		this.addChild( footer );

		var header = new umc.widgets.ContainerWidget( {
			'class': 'umcPageHeader',
			region: 'top'
		} );
		this._cbxSize = new umc.widgets.ComboBox( {
			name: this._( 'Size' ),
			style: 'float: left',
			staticValues: [
				{ id: 200, label: this._( 'tiny' ) },
				{ id: 250, label: this._( 'small' ) },
				{ id: 350, label: this._( 'normal' ) },
				{ id: 500, label: this._( 'large' ) }
			],
			value: 250,
			onChange: dojo.hitch( this, function( newValue ) {
				console.log( 'ComboBox.onChange: ' + newValue );
				if ( this._container.hasChildren() ) {
					dojo.forEach( this._container.getChildren(), dojo.hitch( this, function( child ) {
						child._updateImage( newValue );
					} ) );
				}
			} )
		} );
		header.addChild( this._cbxSize );
		this.addChild( header );

		this._container = new umc.widgets.ContainerWidget({
				scrollable: true
		});
		this.addChild( this._container );
		this.startup();
	},

	_cleanup: function() {
		if ( this._container.hasChildren() ) {
			dojo.forEach( this._container.getChildren(), dojo.hitch( this, function( child ) {
				this._container.removeChild( child );
				child.destroyRecursive();
			} ) );
		}
	},

	load: function( ids ) {
		// during loading show the standby animation
		this.standby(true);
		this._cleanup();
		dojo.forEach( ids, dojo.hitch( this, function( item ) {
			var computer = new umc.modules._computerroom.Item( dojo.mixin( item, {
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




