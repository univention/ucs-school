/*
 * Copyright 2011 Univention GmbH
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
/*global console MyError dojo dojox dijit umc */

dojo.provide("umc.modules._schoolgroups.DetailPage");

dojo.require("umc.dialog");
dojo.require("umc.i18n");
dojo.require("umc.tools");
dojo.require("umc.widgets.Form");
dojo.require("umc.widgets.Page");
dojo.require("umc.widgets.StandbyMixin");

dojo.declare("umc.modules._schoolgroups.DetailPage", [ umc.widgets.Page, umc.widgets.StandbyMixin, umc.i18n.Mixin ], {
	// summary:
	//		This class represents the detail view of our dummy module.

	// reference to the module's store object
	moduleStore: null,

	// specifies the module flavor
	moduleFlavor: null,

	// internal reference to the flavored umcpCommand function
	umcpCommand: null,

	// use i18n information from umc.modules.schoolgroups
	i18nClass: 'umc.modules.schoolgroups',

	// internal reference to the formular containing all form widgets of an UDM object
	_form: null,

	postMixInProperties: function() {
		// is called after all inherited properties/methods have been mixed
		// into the object (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		// set the umcpCommand reference
		this.umcpCommand = this.moduleStore.umcpCommand;

		// Set the opacity for the standby animation to 100% in order to mask
		// GUI changes when the module is opened. Call this.standby(true|false)
		// to enabled/disable the animation.
		this.standbyOpacity = 1;

		// set the page header
		this.headerText = this.moduleFlavor == 'class' ? this._( 'Edit class' ) : this._( 'Edit workgroup' );
		this.helpText = this.moduleFlavor == 'class' ? 
			this._('This page allows to specify teachers who are associated with the class') :
			this._('This page allows to edit workgroup settings and to administrate which teachers/students belong to the group.');

		// configure buttons for the footer of the detail page
		this.footerButtons = [{
			name: 'submit',
			label: this._('Save changes'),
			callback: dojo.hitch(this, function() {
				this._save(this._form.gatherFormValues());
			})
		}, {
			name: 'back',
			label: this._('Back to overview'),
			callback: dojo.hitch(this, 'onClose')
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
		var groups = [];
		if ( this.moduleFlavor == 'workgroup-admin' ) {
			groups.push( { id: 'None', label: this._('All users') } );
		}
		if ( this.moduleFlavor == 'class' || this.moduleFlavor == 'workgroup-admin' ) {
			groups.push( { id: 'teacher', label: this._('All teachers') } );
		}
		if ( this.moduleFlavor == 'workgroup' || this.moduleFlavor == 'workgroup-admin' ) {
			groups.push( { id: 'student', label: this._('All students') } );
		}

		// specify all widgets
		var widgets = [{
			type: 'TextBox',
			name: 'name',
			label: this.moduleFlavor == 'class' ? this._( 'Class' ) : this._( 'Workgroup' ),
			disabled: this.moduleFlavor != 'workgroup-admin',
			required: true
		}, {
			type: 'TextBox',
			name: 'description',
			label: this._('Description'),
			description: this._('Verbose description of the group'),
			disabled: this.moduleFlavor != 'workgroup-admin'
		}, {
			type: 'MultiObjectSelect',
			name: 'members',
			label: this.moduleFlavor == 'class' ? this._( 'Teachers' ) : this.moduleFlavor == 'workgroup' ? this._( 'Students' ) : this._( 'Members' ),
			description: this.moduleFlavor == 'class' ? this._('Teachers of the specified class') : this._('Teachers and students that belong to the current workgroup'),
			queryWidgets: [ {
				type: 'ComboBox',
				name: 'school',
				label: this._('School'),
				dynamicValues: 'schoolgroups/schools',
				umcpCommand: this.umcpCommand,
				autoHide: true
			}, {
				type: 'ComboBox',
				name: 'group',
				label: this._('User group or class'),
				depends: 'school',
				staticValues: groups,
				dynamicValues: 'schoolgroups/classes',
				umcpCommand: this.umcpCommand
			}, {
				type: 'TextBox',
				name: 'pattern',
				label: this._('Name')
			}],
			queryCommand: dojo.hitch(this, function(options) {
				return this.umcpCommand('schoolgroups/users', options).then(function(data) {
					return data.result;
				});
			}),
			queryOptions: dojo.hitch( this, function() {
				if ( this.moduleFlavor == 'class' ) {
					return { group: 'teacher' };
				} else if ( this.moduleFlavor == 'workgroup' ) {
					return { group: 'student' };
				}
				return {};
			} ),
			autoSearch: false
		}];

		// specify the layout... additional dicts are used to group form elements
		// together into title panes
		var layout = [{
			label: this._('Properties'),
			layout: [ 'name', 'description' ]
		}, {
			label: this._('Members'),
			layout: [ 'members' ]
		}];

		// create the form
		this._form = new umc.widgets.Form({
			widgets: widgets,
			layout: layout,
			moduleStore: this.moduleStore
		});

		// add form to page... the page extends a BorderContainer, by default
		// an element gets added to the center region
		this.addChild(this._form);

		// hook to onSubmit event of the form
		this.connect(this._form, 'onSubmit', '_save');
	},

	_save: function( values ) {
		var deferred = null;
		var nameWidget = this._form.getWidget( 'name' );
		if ( ! nameWidget.get( 'value' ) ) {
			nameWidget.setValid( false, this._( 'The group name is required' ) );
			return;
		} else {
			nameWidget.setValid( null );
		}
		if ( values.$dn$ ) {
			deferred = this.moduleStore.put( values );
		} else {
			deferred = this.moduleStore.add( values );
		}
		deferred.then( dojo.hitch( this, function() {
			this.onClose();
		} ) );
	},

	load: function(id) {
		// during loading show the standby animation
		this.standby(true);

		// var nameWidget = this._form.getWidget( 'name' );
		// nameWidget.setValid( null );
		// load the object into the form... the load method returns a
		// dojo.Deferred object in order to handel asynchronity
		this._form.load(id).then(dojo.hitch(this, function() {
			// done, switch of the standby animation
			this.standby(false);
		}), dojo.hitch(this, function() {
			// error handler: switch of the standby animation
			// error messages will be displayed automatically
			this.standby(false);
		}));
	},

	onClose: function(dn, objectType) {
		// event stub 
	}
});



