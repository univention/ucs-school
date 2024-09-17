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
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/aspect",
	"dojo/dom",
	"dojo/dom-class",
	"dojox/html/entities",
	"dijit/layout/ContentPane",
	"dijit/_Contained",
	"dijit/Tooltip",
	"umc/tools",
	"umc/widgets/ComboBox",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Button",
	"umc/widgets/Page",
	"umc/widgets/StandbyMixin",
	"umc/widgets/Text",
	"put-selector/put",
	"umc/i18n!umc/modules/computerroom"
], function(declare, lang, array, aspect, dom, domClass, entities, ContentPane, _Contained, Tooltip, tools,
		ComboBox, ContainerWidget, Button, Page, StandbyMixin, Text, put, _) {

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
	// 	_pattern: '/univention/command/computerroom/screenshot?computer={computer}&random={random}',

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

	var Item = declare("umc.modules.computerroom.Item", [ ContentPane, _Contained ], {

		// the computer to show
		computer: '',

		// current user at the computer
		username: '',

		// image object
		image: null,

		// random extension to the URL to avoid caching
		random: Math.random(),

		// pattern for the image URI
		_pattern: '/univention/command/computerroom/screenshot?computer={computer}&random={random}&size={size}',

		// timer to update the images
		_timer: null,

		uninitialize: function() {
			this.inherited(arguments);
			if (this._timer !== null) {
				window.clearTimeout(this._timer);
			}
		},

		_createURI: function(size) {
			return lang.replace(this._pattern, {
				computer: encodeURIComponent(this.computer),
				random: encodeURIComponent(this.random),
				size: encodeURIComponent(size),
			});
		},

		_updateImage: function() {
			this.random = Math.random();
			var img = dom.byId(lang.replace('img-{computer}', this));
			var userTag = dom.byId(lang.replace('userTag-{computer}', this));

			if (userTag) {
				userTag.innerHTML = entities.encode(this.username) || '<i>' + entities.encode(_('No user logged in')) + '</i>';
			}
			if (img) {
				var new_uri = this._createURI(dijit.byId("screenShotViewSize").value);
				img.src = new_uri;
			}
			if (this._timer) {
				window.clearTimeout(this._timer);
			}
		},

		buildRendering: function() {
			this.inherited(arguments);
			domClass.add(this.domNode, 'screenShotView__imgThumbnail');
			lang.mixin(this, {
				content: lang.replace('<span class="screenShotView__userTag" id="userTag-{computer}"></span><div class="screenShotView__imgWrapper"><img class="screenShotView__img" id="img-{computer}" alt="{alternative}" src="{initialSrc}"></img></div>', {
					computer: entities.encode(this.computer),
					alternative: entities.encode(_('Currently there is no screenshot available. Wait a few seconds.')),
					initialSrc: require.toUrl(lang.replace('dijit/themes/umc/icons/scalable/{image}', {
						image: _('screenshot_notready.svg')
					}))
				})
			});
			// use dijit.Tooltip here to not hide screenshot tooltips if set up in user preferences
			var tooltip = new Tooltip({
				label: lang.replace('<div class="screenShotView__imgTooltip"><img class="screenShotView__img" alt="{1}" id="screenshotTooltip-{0}" src="{2}" /></div>', [
					entities.encode(this.computer),
					entities.encode(_('Currently there is no screenshot available. Wait a few seconds.')),
					require.toUrl(lang.replace('dijit/themes/umc/icons/scalable/{image}', {
						image: _('screenshot_notready.svg')
					}))
				]),
				connectId: [this.domNode],
				onShow: lang.hitch(this, function() {
					var image = dom.byId('img-' + this.computer);
					var imageTooltip = dom.byId('screenshotTooltip-' + this.computer);
					if (!image || !imageTooltip) {
						return;
					}
					if (image.clientWidth / window.innerWidth > 0.66) {
						tooltip.close();
						return;
					}
					imageTooltip.src = this._createURI(1);
				})
			});
			// destroy the tooltip when this widget is destroyed
			aspect.after(this, 'destroy', function() { tooltip.destroy(); });
		},
		startup: function(){
		    this.inherited(arguments);
		    var getUCR = tools.ucr(['ucsschool/umc/computerroom/screenshot/interval']);
		    getUCR.then(lang.hitch(this, function(result) {
			var img = dom.byId(lang.replace('img-{computer}', this));
			var updateInterval = result['ucsschool/umc/computerroom/screenshot/interval'] || 5;
			img.addEventListener('load', () => this._timer = window.setTimeout(lang.hitch(this, '_updateImage'), updateInterval * 1000));
			img.addEventListener('error', () => this._timer = window.setTimeout(lang.hitch(this, '_updateImage'), updateInterval * 1000));
			this._updateImage();
		    }));
		},

	} );

	return declare("umc.modules.computerroom.ScreenshotView", [ Page, StandbyMixin ], {
		// summary:
		//		This class represents the screenshot view

		// internal reference to the flavored umcpCommand function
		umcpCommand: null,

		fullWidth: true,

		navContentClass: 'umcCard2',
		mainContentClass: 'umcCard2',

		_container: null,
		_noComputersText: null,

		_cbxSize: null,

		postMixInProperties: function() {
			this.inherited(arguments);

			// set the page header
			this.headerText = _('Screenshots of computers');
			this.helpText = _('This page shows screenshots of selected computers that will be updated continuously.');
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			this.inherited(arguments);

			var headerButtons = [{
				name: 'close',
				label: _('Back to overview'),
				iconClass: 'arrow-left',
				onClick: lang.hitch(this, function() {
					this._cleanup();
					this.onClose();
				})
			}];

			this.set('headerButtons', headerButtons);

			this._cbxSize = new ComboBox( {
				region: 'nav',
				name: _('Size'),
				staticValues: [
					{ id: 4, label: _('Tiny') },
					{ id: 3, label: _('Small') },
					{ id: 2, label: _('Normal') },
					{ id: 1, label: _('Large') }
				],
				value: 3,
				id: "screenShotViewSize",
				onChange: lang.hitch(this, function(newValue) {
					put(this._container.domNode, `[style="--local-columns-count: ${newValue}"]`);
				} )
			} );
			this.addChild(this._cbxSize);

			this._container = new ContainerWidget({
				'class': 'screenShotView__screenshotContainer'
			});
			this.addChild(this._container);

			this._noComputersText = new Text({
				'class': 'screenShotView__noComputersText',
				content: entities.encode(_('All computers in this room are offline.')),
				visible: false
			});
			this.addChild(this._noComputersText);
		},

		_cleanup: function() {
			this._container.destroyDescendants();
		},

		load: function(ids) {
			// during loading show the standby animation
			this.standby(true);
			this._cleanup();
			array.forEach(ids, lang.hitch(this, function(item) {
				var computer = new Item(item);
				this._container.addChild(computer);
			}));
			this._noComputersText.set('visible', !this._container.hasChildren());
			this.startup();
			this.standby(false);
		},

		onClose: function() {
			// event stub
		}
	});
});
