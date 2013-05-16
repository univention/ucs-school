/*
 * Copyright 2013 Univention GmbH
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
/*global define window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/Deferred",
	"dojo/data/ItemFileWriteStore",
	"dojo/store/DataStore",
	"dojo/store/Memory",
	"umc/tools",
	"umc/widgets/Grid",
	"umc/widgets/Text",
	"umc/i18n!umc/modules/schoolexam"
], function(declare, lang, array, Deferred, ItemFileWriteStore, DataStore, Memory, tools, Grid, Text, _) {
	// helper function that sanitizes a given filename
	var sanitizeFilename = function(name) {
		array.forEach([/\//g, /\\/g, /\?/g, /%/g, /\*/g, /:/g, /\|/g, /"/g, /</g, />/g, /\$/g, /'/g], function(ichar) {
			name = name.replace(ichar, '_');
		});

		// limit the filename length
		return name.slice(0, 255);
	};

	return declare("umc.modules.schoolexam.RebootGrid", [ Grid ], {
		minUpdateDelay: 20,
		maxUpdateDelay: 120,
		offsetUpdateDelay: 20,
		room: null,

		_lastUpdate: 0,
		_firstUpdate: 0,
		_updateTimer: null,

		// state that indicates 
		_monitoringDone: false,

		style: 'height: 250px; width: 100%;',
		cacheRowWidgets: false,

		constructor: function() {
			this.moduleStore = new Memory();
			this.columns = [{
				name: 'name',
				label: _('Name'),
				formatter: lang.hitch(this, function(value, rowIndex) {
					var item = this._grid.getItem(rowIndex);
					var icon = 'offline';
					if (item.connection[0] == 'connected') {
						icon = 'demo-offline';
					} 
					var widget = new Text({});
					widget.set('content', lang.replace('<img src="{path}/16x16/computerroom-{icon}.png" height="16" width="16" style="float:left; margin-right: 5px" /> {value}', {
						path: require.toUrl('dijit/themes/umc/icons'),
						icon: icon,
						value: value
					}));
					return widget;
				})
			}, {
				name: 'user',
				label: _('User')
			}];
		},
		
		monitorRoom: function(room) {
			// monitoring is only one time possible
			if (this._monitoringDone) {
				return;
			}
			
			// save room
			this.set('room', room);

			// query new list of entries and populate store
			tools.umcpCommand('computerroom/room/acquire', {
				room: room
			}).then(lang.hitch(this, function() {
				this.umcpCommand('computerroom/query').then(lang.hitch(this, function(response) {
					this._initGridData(response.result);
					this._lastUpdate = new Date();
					this._firstUpdate = new Date();
					this.standby(true);
					this._updateRooms();
				}));
			}));
		},

		onMonitoringDone: function() {
			// event stub
			this.standby(false);
			this._monitoringDone = true;
		},

		reboot: function() {
			// get all connected computers
			var computers = [];
			this.moduleStore.query().forEach(function(iitem) {
				if (iitem.connection == 'connected') {
					computers.push(iitem);
				}
			});

			// switch the computers on and update the progress of a Deferred
			// do not reboot all computers at once, use an offset of 300ms
			var deferred = new Deferred();
			var percentPerItem = 100.0 / (computers.length + 1);
			array.forEach(computers, lang.hitch(this, function(iitem, idx) {
				window.setTimeout(lang.hitch(this, function() {
					// trigger reboot
					this.umcpCommand('computerroom/computer/state', {
						computer: iitem.id,
						state: 'restart'
					}, false);

					// update progress
					deferred.progress((1 + idx) * percentPerItem, iitem.id);
				}), idx * 300);
			}));

			// set timeout for finished event
			window.setTimeout(function() {
				deferred.resolve();
			}, 300 * computers.length);

			return deferred;
		},

		_initGridData: function(data) {
			// set up the store objects for the grid
			// create a data store and wrap it in order to have a object store
			// available for easier access
			var dataStore = new ItemFileWriteStore({data: {
				identifier: 'id',
				label: 'name',
				items: data
			}});
			var store = new DataStore({
				store: dataStore,
				idProperty: 'id'
			});
			this.moduleStore = store;
			this._dataStore = dataStore;
			this._grid.setStore(dataStore);
		},

		_updateRooms: function() {
			// get the current delays and see wether they are due
			var delayTotal = (new Date() - this._firstUpdate) / 1000.0;
			var offset = (new Date() - this._lastUpdate) / 1000.0;
			if (delayTotal > this.maxUpdateDelay) {
				// done :)
				this.onMonitoringDone();
				return;
			}
			if (offset > this.offsetUpdateDelay && delayTotal > this.minUpdateDelay) {
				// done :)
				this.onMonitoringDone();
				return;
			}

			var update = function() {
				this._updateTimer = window.setTimeout(lang.hitch(this, '_updateRooms'), 1000);
			};

			this.umcpCommand('computerroom/update', {}, false).then(lang.hitch(this, function(response) {
				var result = response.result;
				if (result.locked) {
					// somebody stole our session... acquire the room again
					tools.umcpCommand('computerroom/room/acquire', {
						room: this.room
					}).then(lang.hitch(this, update), lang.hitch(this, update));
				}

				// update store with information about the computers
				array.forEach(result.computers, function(item) {
					var currentItem = this.moduleStore.get(item.id) || {};
					this.moduleStore.put(lang.mixin(currentItem, item));

					// update _lastUpdate if the connection has changed
					if ('connection' in item) {
						this._lastUpdate = new Date();
					}
				}, this);

				// update status again
				lang.hitch(this, update)();
			}));
		},

		uninitialize: function() {
			this.inherited(arguments);
			if (this._updateTimer !== null) {
				window.clearTimeout(this._updateTimer);
			}
		}
	});
});
