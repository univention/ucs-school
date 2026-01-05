/*
 * SPDX-FileCopyrightText: 2012-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/dom",
	"dojo/dom-class",
	"dojo/on",
	"dojo/dom-style",
	"dojox/html/entities",
	"dijit/layout/ContentPane",
	"dijit/_Contained",
	"umc/tools",
	"umc/widgets/ComboBox",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Page",
	"umc/widgets/StandbyMixin",
	"umc/widgets/Text",
	"put-selector/put",
	"umc/i18n!umc/modules/computerroom"
], function(declare, lang, array, dom, domClass, on, domStyle, entities, ContentPane, _Contained, tools,
		ComboBox, ContainerWidget, Page, StandbyMixin, Text, put, _) {

	var Item = declare("umc.modules.computerroom.Item", [ ContentPane, _Contained ], {

		// the computer to show
		computer: '',

		// objStore containing infos about the computers
		objStore: null,

		// fallback message if no user is logged in
		noUsernameMsg: '<i>' + entities.encode(_('No user logged in')) + '</i>',

		// pattern for the image URI
		_pattern: '/univention/command/computerroom/screenshot?computer={computer}&random={random}&size={size}',

		// fallback if no screenshot can be loaded
		_initialSrc: require.toUrl(lang.replace('dijit/themes/umc/icons/scalable/{image}',
			{ image: _('screenshot_notready.svg') }
		)),

		// store the last cached screenshot url
		_lastImgUrl: null,

		// timers to update the images
		_timer: null,
		_timerLarge: null,

		uninitialize: function() {
			this.inherited(arguments);
			if (this._timer !== null) {
				window.clearTimeout(this._timer);
			}
			if (this._timerLarge !== null) {
				window.clearTimeout(this._timerLarge);
			}
		},

		_createURI: function(size) {
			return lang.replace(this._pattern, {
				computer: encodeURIComponent(this.computer),
				random: encodeURIComponent(Math.random()),
				size: encodeURIComponent(size),
			});
		},

		_updateImage: function() {
			var userTag = dom.byId(lang.replace('userTag-{computer}', this));
			var img = dom.byId(lang.replace('img-{computer}', this));
			if (userTag) {
				userTag.innerHTML = entities.encode(this.objStore.get(this.computer)["user"]) || this.noUsernameMsg;
			}
			if (img) {
				var new_uri = this._createURI(dijit.byId("screenShotViewSize").value);
				img.src = new_uri;
			}
		},
		_updateImageLarge: function() {
			var imgLarge = dom.byId(lang.replace('img-large-{computer}', this));
			var imgLargeDiv = dom.byId(lang.replace('img-large-{computer}-overlay', this));
			var userTag = dom.byId(lang.replace('userTag-large-{computer}', this));
			if (domStyle.get(imgLargeDiv, "display") === "none") {
				return;
			}
			if (userTag) {
				userTag.innerHTML = entities.encode(this.objStore.get(this.computer)["user"]) || this.noUsernameMsg;
			}
			if (imgLarge) {
				var new_uri = this._createURI(1);
				imgLarge.src = new_uri;
			}
		},

		buildRendering: function() {
			this.inherited(arguments);
			domClass.add(this.domNode, 'screenShotView__imgThumbnail');
			lang.mixin(this, {
				content: lang.replace(
					`
<span class="screenShotView__userTag" id="userTag-{computer}">{username}</span>
<div id="img-{computer}-wrapper" class="screenShotView__imgWrapper">
	<img class="screenShotView__img" id="fallback-{computer}" alt="{alternative}" src="{initialSrc}">
	<img class="screenShotView__img" id="img-{computer}" title="{title}" style="display: none">
</div>
<div id="img-large-{computer}-overlay" class="screenShotView__large_imgOverlay">
	<figure class=screenShotView__figure>
		<div class="screenShotView__large_caption-container"></div>
		<div class="screenShotView__large_imgWrapper">
			<img class="screenShotView__large_img" id="fallback-large-{computer}" alt="{alternative}" src="{initialSrc}">
			<img class="screenShotView__large_img" id="img-large-{computer}" title="{titleLarge}" style="display: none">
		</div>
		<div class="screenShotView__large_caption-container">
			<figcaption id='userTag-large-{computer}'>{username}</figcaption>
		</div>
	</figure>
</div>
					`, {
					computer: entities.encode(this.computer),
					alternative: entities.encode(_('Currently there is no screenshot available. Wait a few seconds.')),
					initialSrc: this._initialSrc,
					username: entities.encode(this.objStore.get(this.computer)["user"]) || this.noUsernameMsg,
					title: entities.encode(_("Click to zoom in")),
					titleLarge: entities.encode(_("Click to close"))
				})
			});
		},
		startImageUpdate: function() {
			var getUCR = tools.ucr(['ucsschool/umc/computerroom/screenshot/interval']);
			var img = dom.byId(lang.replace('img-{computer}', this));
			var imgLarge = dom.byId(lang.replace('img-large-{computer}', this));
			var fallback = dom.byId(lang.replace('fallback-{computer}', this));
			var fallbackLarge = dom.byId(lang.replace('fallback-large-{computer}', this));
			return getUCR.then(lang.hitch(this, function(result) {
				var updateInterval = result['ucsschool/umc/computerroom/screenshot/interval'] || 5;
				img.addEventListener("load", (evt) => {
					domStyle.set(fallback, "display", "none");
					domStyle.set(img, "display", "");
					this._lastImgUrl = img.src;
					if (this._timer) {
						window.clearTimeout(this._timer);
					}
					this._timer = window.setTimeout(
						lang.hitch(this, '_updateImage'),
						updateInterval * 1000
					)
				});
				imgLarge.addEventListener("load", (evt) => {
					domStyle.set(fallbackLarge, "display", "none");
					domStyle.set(imgLarge, "display", "");
					if (this._timerLarge) {
						window.clearTimeout(this._timerLarge);
					}
					this._timerLarge = window.setTimeout(
						lang.hitch(this, '_updateImageLarge'),
						updateInterval * 1000
					)
				});
				img.addEventListener("error", (evt) => {
					domStyle.set(img, "display", "none");
					domStyle.set(fallback, "display", "");
					this._lastImgUrl = null;
					if (this._timer) {
						window.clearTimeout(this._timer);
					}
					this._timer = window.setTimeout(
						lang.hitch(this, '_updateImage'),
						updateInterval * 1000
					)
				});
				imgLarge.addEventListener("error", (evt) => {
					domStyle.set(imgLarge, "display", "none");
					domStyle.set(fallbackLarge, "display", "");
					if (this._timerLarge) {
						window.clearTimeout(this._timerLarge);
					}
					this._timerLarge = window.setTimeout(
						lang.hitch(this, '_updateImageLarge'),
						updateInterval * 1000
					)
				});
				this._updateImage();
			}));
		},
		startup: function(){
			this.inherited(arguments);
			this.startImageUpdate();
			var img = dom.byId(lang.replace('img-{computer}', this));
			var imgDiv = dom.byId(lang.replace('img-{computer}-wrapper', this));
			var imgLarge = dom.byId(lang.replace('img-large-{computer}', this));
			var fallbackLarge = dom.byId(lang.replace('fallback-large-{computer}', this));
			var largeImgDiv = dom.byId(lang.replace('img-large-{computer}-overlay', this));
			on(imgDiv, "click", lang.hitch(this, function(evt){
				domStyle.set(largeImgDiv, "display", "block");
				if (this._lastImgUrl) {
					imgLarge.src = this._lastImgUrl;  // Should be cached and can be shown immediatly
					domStyle.set(fallbackLarge, "display", "none");
					domStyle.set(imgLarge, "display", "");
					this._updateImageLarge();
				} else {
					domStyle.set(imgLarge, "display", "none");
					domStyle.set(fallbackLarge, "display", "");
					this._updateImageLarge();
				}
			}));
			on(largeImgDiv, "click", lang.hitch(this, function(evt){
				domStyle.set(largeImgDiv, "display", "none");
				if (this._timerLarge) {
					window.clearTimeout(this._timerLarge);
				}
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
			this.headerText = entities.encode(_('Screenshots of computers'));
			this.helpText = entities.encode(_('This page shows screenshots of selected computers that will be updated continuously.'));
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			this.inherited(arguments);

			var headerButtons = [{
				name: 'close',
				label: entities.encode(_('Back to overview')),
				iconClass: 'arrow-left',
				onClick: lang.hitch(this, function() {
					this._cleanup();
					this.onClose();
				})
			}];

			this.set('headerButtons', headerButtons);

			this._cbxSize = new ComboBox( {
				region: 'nav',
				name: entities.encode(_('Size')),
				staticValues: [
					{ id: 9, label: _('Tiny') },
					{ id: 6, label: _('Small') },
					{ id: 3, label: _('Normal') },
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
			styleUmcModuleWrapper({"width": "100%"});
			this.standby(false);
		},

		onClose: function() {
			styleUmcModuleWrapper({"width": ""});
		}
	});
});


// Wrapper to resize the screenShotView to 100% width. To achieve this a parent
// with CSS class "umcModuleWrapper" has to get "width: 100%" assigned.
// This shall only happen, on the parent Wrapper element with CSS class
// "screenShotView__screenshotContainer",
// because "umcModuleWrapper" is used for multiple UMC modules.
function styleUmcModuleWrapper(style) {
	const childElements = document.querySelectorAll('.screenShotView__screenshotContainer');

	childElements.forEach(childElement => {
		const parentElement = childElement.closest('.umcModuleWrapper');
		if (parentElement) {
			parentElement.style.width = style["width"];
		}
	});
}
