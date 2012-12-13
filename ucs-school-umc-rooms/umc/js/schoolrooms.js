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
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/dialog",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Grid",
	"umc/widgets/Module",
	"umc/widgets/Page",
	"umc/widgets/SearchForm",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolrooms/DetailPage",
	"umc/i18n!/umc/modules/schoolrooms"
], function(declare, lang, dialog, ExpandingTitlePane, Grid, Module, Page, SearchForm, TextBox, ComboBox, DetailPage, _) {

return declare("umc.modules.schoolrooms", [ Module ], {
	// summary:
	//		Template module to ease the UMC module development.
	// description:
	//		This module is a template module in order to aid the development of
	//		new modules for Univention Management Console.

	// the property field that acts as unique identifier for the object
	idProperty: '$dn$',

	// internal reference to the grid
	_grid: null,

	// internal reference to the search page
	_searchPage: null,

	// internal reference to the detail page for editing an object
	_detailPage: null,

	postMixInProperties: function() {
		// is called after all inherited properties/methods have been mixed
		// into the object (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		// Set the opacity for the standby animation to 100% in order to mask
		// GUI changes when the module is opened. Call this.standby(true|false)
		// to enabled/disable the animation.
		this.standbyOpacity = 1;
	},

	buildRendering: function() {
		// is called after all DOM nodes have been setup
		// (originates from dijit._Widget)

		// it is important to call the parent's postMixInProperties() method
		this.inherited(arguments);

		// start the standby animation in order prevent any interaction before the
		// form values are loaded
		this.standby(true);

		// render the page containing search form and grid
		this.renderSearchPage();
	},

	renderSearchPage: function(containers, superordinates) {
		// render all GUI elements for the search formular and the grid

		// setup search page and its main widgets
		// for the styling, we need a title pane surrounding search form and grid
		this._searchPage = new Page({
			headerText: this.description,
			helpText: ''
		});

		// umc.widgets.Module is also a StackContainer instance that can hold
		// different pages (see also umc.widgets.TabbedModule)
		this.addChild(this._searchPage);

		// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
		var titlePane = new ExpandingTitlePane({
			title: _('Search results')
		});
		this._searchPage.addChild(titlePane);


		//
		// data grid
		//

		// define grid actions
		var actions = [{
			name: 'add',
			label: _('Add room'),
			description: _('Create a new room'),
			iconClass: 'umcIconAdd',
			isContextAction: false,
			isStandardAction: true,
			callback: lang.hitch(this, '_addObject')
		}, {
			name: 'edit',
			label: _('Edit'),
			description: _('Edit the selected object'),
			iconClass: 'umcIconEdit',
			isStandardAction: true,
			isMultiAction: false,
			callback: lang.hitch(this, '_editObject')
		}, {
			name: 'delete',
			label: _('Delete'),
			description: _('Deleting the selected objects.'),
			isStandardAction: true,
			isMultiAction: false,
			iconClass: 'umcIconDelete',
			callback: lang.hitch(this, '_deleteObjects')
		}];

		// define the grid columns
		var columns = [{
			name: 'name',
			label: _('Name'),
			width: '40%'
		}, {
			name: 'description',
			label: _('Description'),
			width: '60%'
		}];

		// generate the data grid
		this._grid = new Grid({
			// property that defines the widget's position in a dijit.layout.BorderContainer,
			// 'center' is its default value, so no need to specify it here explicitely
			// region: 'center',
			actions: actions,
			// defines which data fields are displayed in the grids columns
			columns: columns,
			// a generic UMCP module store object is automatically provided
			// as this.moduleStore (see also store.getModuleStore())
			moduleStore: this.moduleStore,
			// initial query
			query: {}
		});

		// add the grid to the title pane
		titlePane.addChild(this._grid);


		//
		// search form
		//

		// add remaining elements of the search form
		var widgets = [{
			type: ComboBox,
			name: 'school',
			description: _('Choose the school'),
			label: _('School'),
			dynamicValues: 'schoolrooms/schools',
            onDynamicValuesLoaded: lang.hitch( this, function( result ) {
                this._detailPage.set( 'schools', result );
            } ),
			autoHide: true
		}, {
			type: TextBox,
			name: 'pattern',
			description: _('Specifies the substring pattern which is searched for in the displayed name'),
			label: _('Search pattern')
		}];

		// the layout is an 2D array that defines the organization of the form elements...
		// here we arrange the form elements in one row and add the 'submit' button
		var layout = [
			[ 'school', 'pattern', 'submit' ]
		];

		// generate the search form
		this._searchForm = new SearchForm({
			// property that defines the widget's position in a dijit.layout.BorderContainer
			region: 'top',
			widgets: widgets,
			layout: layout,
			onSearch: lang.hitch(this, function(values) {
				// call the grid's filter function
				if (values.school) {
					this._grid.filter(values);
				}
			})
		});

		// turn off the standby animation as soon as all form values have been loaded
		this._searchForm.on('ValuesInitialized', lang.hitch(this, function() {
			this.standby(false);
			var values = this._searchForm.get('value');
			if (values.school) {
				this._grid.filter(values);
			}
		}));

		// add search form to the title pane
		titlePane.addChild(this._searchForm);

		//
		// conclusion
		//

		// we need to call page's startup method manually as all widgets have
		// been added to the page container object
		this._searchPage.startup();

		// create a DetailPage instance
		this._detailPage = new DetailPage({
			moduleStore: this.moduleStore
		});
		this.addChild(this._detailPage);

		// connect to the onClose event of the detail page... we need to manage
		// visibility of sub pages here
		this._detailPage.on('close', lang.hitch(this, function() {
			this.selectChild(this._searchPage);
		}));
	},

	_addObject: function() {
		this._detailPage._form.clearFormValues();
        this._detailPage.set( 'school', this._searchForm.getWidget( 'school' ).get( 'value' ) );
        this._detailPage.disable( 'school', false );

		this._detailPage.set( 'headerText', _( 'Add room' ) );
		this._detailPage.set('helpText', _('Create room and assign computers'));
		this.selectChild( this._detailPage );
	},

	_editObject: function(ids, items) {
		if (ids.length != 1) {
			// should not happen
			return;
		}

		this.selectChild(this._detailPage);
        this._detailPage.disable( 'school', true );
		this._detailPage.set( 'headerText', _( 'Edit room' ) );
		this._detailPage.set('helpText', _('Edit room and assign computers'));
		this._detailPage.load(ids[0]);
	},

	_deleteObjects: function(ids, items) {
		dialog.confirm( lang.replace( _( 'Should the room {name} be deleted?' ), items[ 0 ] ), [ {
			name: 'cancel',
			'default' : true,
			label: _( 'Cancel' )
		}, {
			name: 'delete',
			label: _( 'Delete' )
		} ] ).then( lang.hitch( this, function( action ) {
			if ( action != 'delete' ) {
				return;
			}
			this.standby(true);
			this.moduleStore.remove(ids).then(lang.hitch(this, function(response) {
				this.standby(false);
				if (response.success === true) {
					dialog.alert(_('The room has been deleted successfully'));
				} else {
					dialog.alert(lang.replace(_('The room could not be deleted ({message})'), response));
				}
			}));

		} ) );
	}
});

});
