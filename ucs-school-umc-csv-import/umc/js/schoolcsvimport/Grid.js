/*
 * Copyright 2014-2015 Univention GmbH
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
	"dojo/aspect",
	"dijit/Menu",
	"dijit/layout/BorderContainer",
	"dojox/grid/EnhancedGrid",
	"umc/widgets/StandbyMixin",
	"umc/widgets/ContainerWidget",
	"umc/widgets/Grid"
], function(declare, lang, aspect, Menu, BorderContainer, EnhancedGrid, StandbyMixin, ContainerWidget, Grid) {
	var _Grid = declare([EnhancedGrid], {
		// this is done in umc/widgets/Grid.
		// causes problems with Memory()
		//_fetch: function(start, isRender) {
		//	// force start=0
		//	arguments[0] = 0;
		//	this.inherited(arguments);
		//}
	});

	return declare('umc.modules.schoolcsvimport.Grid', [ Grid ], {
		// FIXME: ugly fork of Grid.
		// put the buildRendering into umc.widgets.Grid!!!
		// change is lang.mixin() in this._grid = ...
		buildRendering: function() {
			BorderContainer.prototype.buildRendering.apply(this, arguments);
			StandbyMixin.prototype.buildRendering.apply(this, arguments);

			// create right-click context menu
			this._contextMenu = new Menu({});
			this.own(this._contextMenu);

			// add a header for the grid
			this._header = new ContainerWidget({
				region: 'top',
				'class': 'umcGridHeader'
			});
			this.addChild(this._header);

			// create the grid
			this._grid = new _Grid(lang.mixin({
				store: this._dataStore,
				region: 'center',
				query: this.query,
				queryOptions: { ignoreCase: true },
				'class': 'umcGrid',
				rowsPerPage: 30,
				plugins : {
					indirectSelection: {
						headerSelector: true,
						name: 'Selection',
						width: '25px',
						styles: 'text-align: center;'
					},
					menus: {
						rowMenu: this._contextMenu
					}
				}/*,
				canSort: lang.hitch(this, function(col) {
					// disable sorting for the action columns
					return Math.abs(col) - 2 < this.columns.length && Math.abs(col) - 2 >= 0;
				})*/
			}, this.gridOptions || {}));

			// add a footer for the grid
			this._footer = new ContainerWidget({
				region: 'bottom',
				'class': 'umcGridFooter'
			});
			this._createFooter();

			// update columns and actions
			this.setColumnsAndActions(this.columns, this.actions);
			if (typeof this.sortIndex == "number") {
				this._grid.setSortIndex(Math.abs(this.sortIndex), this.sortIndex > 0);
			}

			this.addChild(this._grid);
			this.addChild(this._footer);

			//
			// register event handler
			//

			// in case of any changes in the module store, refresh the grid
			// FIXME: should not be needed anymore with Dojo 1.8
			if (this.moduleStore.on && this.moduleStore.onChange) {
				this.own(this.moduleStore.on('Change', lang.hitch(this, function() {
					this.filter(this.query);
				})));
			}

			this.own(aspect.after(this._grid, "_onFetchComplete", lang.hitch(this, '_onFetched', true)));
			this.own(aspect.after(this._grid, "_onFetchError", lang.hitch(this, '_onFetched', false)));

			this._grid.on('selectionChanged', lang.hitch(this, '_selectionChanged'));
			this._grid.on('cellContextMenu', lang.hitch(this, '_updateContextItem'));

			this._grid.on('rowClick', lang.hitch(this, '_onRowClick'));

			// make sure that we update the disabled items after sorting etc.
			this.own(aspect.after(this._grid, '_refresh', lang.hitch(this, '_updateDisabledItems')));
		}
	});
});

