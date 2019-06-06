/*
 * Copyright 2011-2019 Univention GmbH
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
	"umc/widgets/Text",
	"umc/widgets/ComboBox",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/Grid",
	"umc/widgets/StandbyMixin",
	"umc/i18n!umc/modules/schoolrooms"
], function(declare, lang, array, tools, Page, Form, TextBox, Text, ComboBox, MultiObjectSelect, Grid, StandbyMixin, _) {

	return declare("umc.modules.schoolrooms.DetailPage", [ Page, StandbyMixin ], {
		moduleStore: null,

		_form: null,
		_grid: null,

		postMixInProperties: function() {
			this.inherited(arguments);

			this.headerText = '';
			this.helpText = '';

			// configure buttons for the header of the detail page, overwriting
			// the close button
			this.headerButtons = [{
				name: 'submit',
				label: _('Save'),
				iconClass: 'umcSaveIconWhite',
				callback: lang.hitch(this, function() {
					this._save(this._form.get('value'));
				})
			}, {
				name: 'close',
				label: _('Cancel'),
				iconClass: 'umcArrowLeftIconWhite',
				callback: lang.hitch(this, 'onClose')
			}];
		},

		buildRendering: function() {
			this.inherited(arguments);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
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

			this._form.getWidget('computers').on('ShowDialog', lang.hitch(this, function(_dialog) {
				_dialog._form.getWidget('school').setInitialValue(this._form.getWidget('school').get('value'), true);
			}));

			// hook to onSubmit event of the form
			this._form.on('submit', lang.hitch(this, '_save'));

			this._grid = new Grid({
				actions: [],
				columns: [{
					name: 'label',
					label: _('Computers')
				}],
				moduleStore: this._form.getWidget('computers')._objectStore,
				query: {}
			});

			this._form.getWidget('computers').watch('value', lang.hitch(this, function() {
				this._grid.update(true)
			}));
			this.addChild(Text({
				name: 'grid_title',
				content: '<h2>' + _('Teacher computer') + '</h2>'
			}));
			this.addChild(this._grid);
		},

		_save: function() {
			var values = this._form.get('value');
			values['teacher_computers'] = this._grid.getSelectedIDs();
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
				// may return false in case room.name was already taken
				deferred.then(lang.hitch(this, function(success) {
					if (!success) {
						this.addNotification(_('Room %s not created. It already exists.', values.name));
					}
				}));
			}

			this.standbyDuring(deferred);
			deferred.then(lang.hitch(this, function() {
				this.onClose();
			}));
		},

		load: function(id) {
			this.standbyDuring(this._form.load(id));
		},

		onClose: function(dn, objectType) {
			// event stub
		},

		disable: function(field, disable) {
			this._form.getWidget(field).set('disabled', disable);
		},

		_setSchoolAttr: function(school) {
			this._form.getWidget('school').set('value', school);
		},

		_setSchoolsAttr: function(schools) {
			var school = this._form.getWidget('school');
			school.set('staticValues', schools);
			school.set('visible', schools.length > 1);
		}

	});

});
