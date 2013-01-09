/*
 * Copyright 2011-2012 Univention GmbH
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
	"umc/tools",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/StandbyMixin",
	"umc/i18n!/umc/modules/schoolrooms"
], function(declare, lang, array, tools, Page, Form, TextBox, ComboBox, MultiObjectSelect, StandbyMixin, _) {

	return declare("umc.modules.schoolrooms.DetailPage", [ Page, StandbyMixin ], {
		// reference to the module's store object
		moduleStore: null,

		// internal reference to the formular containing all form widgets of an UDM object
		_form: null,

		postMixInProperties: function() {
			// is called after all inherited properties/methods have been mixed
			// into the object (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			// Set the opacity for the standby animation to 100% in order to mask
			// GUI changes when the module is opened. Call this.standby(true|false)
			// to enabled/disable the animation.
			this.standbyOpacity = 1;

			// set the page header
			this.headerText = _('');
			this.helpText = _('');

			// configure buttons for the footer of the detail page
			this.footerButtons = [{
				name: 'submit',
				label: _('Save'),
				callback: lang.hitch(this, function() {
					this._save(this._form.get('value'));
				})
			}, {
				name: 'cancel',
				label: _('Cancel'),
				callback: lang.hitch(this, 'onClose')
			}];
		},

		buildRendering: function() {
			// is called after all DOM nodes have been setup
			// (originates from dijit._Widget)

			// it is important to call the parent's postMixInProperties() method
			this.inherited(arguments);

			this.renderDetailPage();
		},

		renderDetailPage: function() {
			// render the form containing all detail information that may be edited

			// specify all widgets
			var widgets = [{
				type: ComboBox,
				name: 'school',
				label: _( 'School' ),
				staticValues: []
			}, {
				type: TextBox,
				name: 'name',
				label: _('Name'),
				required: true
			}, {
				type: TextBox,
				name: 'description',
				label: _('Description'),
				description: _('Verbose description of the current group')
			}, {
				type: MultiObjectSelect,
				name: 'computers',
				label: _('Computers in the room'),
				queryWidgets: [{
					type: ComboBox,
					name: 'school',
					label: _('School'),
					dynamicValues: 'schoolrooms/schools',
					autoHide: true
				}, {
					type: TextBox,
					name: 'pattern',
					label: _('Search pattern')
				}],
				queryCommand: lang.hitch(this, function(options) {
					return tools.umcpCommand('schoolrooms/computers', options).then(function(data) {
						return data.result;
					});
				}),
				formatter: function(dnList) {
					var tmp = array.map(dnList, function(idn) {
						if (typeof idn === 'string') {
							return {
								id: idn,
								label: tools.explodeDn(idn, true).shift() || ''
							};
						} else { return idn; }
					});
					return tmp;
				},
				autoSearch: false
			}];

			// specify the layout... additional dicts are used to group form elements
			// together into title panes
			var layout = [{
				label: _('Properties'),
				layout: [ 'school', 'name', 'description' ]
			}, {
				label: _('Computers'),
				layout: [ 'computers' ]
			}];

			// create the form
			this._form = new Form({
				widgets: widgets,
				layout: layout,
				moduleStore: this.moduleStore,
				scrollable: true
			});

			// add form to page... the page extends a BorderContainer, by default
			// an element gets added to the center region
			this.addChild(this._form);

        	this._form.getWidget( 'computers' ).on('ShowDialog', lang.hitch( this, function( _dialog ) {
            	_dialog._form.getWidget( 'school' ).setInitialValue( this._form.getWidget( 'school' ).get( 'value' ), true );
        	} ) );

			// hook to onSubmit event of the form
			this._form.on('submit', lang.hitch(this, '_save'));
		},

		_save: function() {
			var values = this._form.get('value');
			var deferred = null;
			var nameWidget = this._form.getWidget('name');

			if (! this._form.validate()){
				nameWidget.focus();
				return;
			}

			if (values.$dn$) {
				deferred = this.moduleStore.put(values);
			} else {
				deferred = this.moduleStore.add(values);
			}

			deferred.then(lang.hitch(this, function() {
				this.onClose();
			}));
		},

		load: function(id) {
			// during loading show the standby animation
			this.standby(true);

			// load the object into the form... the load method returns a
			// Deferred object in order to handel asynchronity
			this._form.load(id).then(lang.hitch(this, function() {
				// done, switch of the standby animation
				this.standby(false);
			}), lang.hitch(this, function() {
				// error handler: switch of the standby animation
				// error messages will be displayed automatically
				this.standby(false);
			}));
		},

		onClose: function(dn, objectType) {
			// event stub 
		},

		disable: function( field, disable ) {
			this._form.getWidget( field ).set( 'disabled', disable );
		},

		_setSchoolAttr: function( school ) {
			this._form.getWidget( 'school' ).set( 'value', school );
		},

		_setSchoolsAttr: function( schools ) {
			var school = this._form.getWidget( 'school' );
			school.set( 'staticValues', schools );
			school.set( 'visible', schools.length > 1 );
		}

	});

});
