/*
 * Copyright 2013-2015 Univention GmbH
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
/*global require define window*/

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
	return declare("umc.modules.schoolexam.RebootGrid", [ Grid ], {
		minUpdateDelay: 20,
		maxUpdateDelay: 120,
		offsetUpdateDelay: 20,
		room: null,

		_lastUpdate: 0,
		_firstUpdate: 0,
		_updateTimer: null,

		constructor: function() {
			this.moduleStore = new Memory();
			this.actions = [{
				name: 'reboot_all',
				label: _('Reboot student computers'),
				isContextAction: false,
				callback: lang.hitch(this, 'onReboot')
			}, {
				name: 'reboot',
				label: _('Reboot selected computers'),
				isMultiAction: true,
				isStandardAction: true,
				canExecute: function(item) {
					return item.connection == 'connected'/* && !item.teacher*/;
				},
				enablingMode: 'some',
				callback: lang.hitch(this, 'onReboot')
			}];
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
				name: 'connection',
				label: _('Reboot'),
				formatter: lang.hitch(this, function(value, rowIndex) {
					var item = this._grid.getItem(rowIndex);
					if (item.teacher[0]) {
						// indicate that a reboot is not necessary for teacher computers
						return _('No reboot necessary');
					}
					if (value == 'connected') {
						// connected machine
						return _('Reboot necessary');
					}
					// no connection
					return _('Not connected / powered down');
				})
			}, {
				name: 'user',
				label: _('User')
			}];
		},

		monitorRoom: function(room) {
			// save room
			this.set('room', room);

			// query new list of entries and populate store
			this.standbyDuring(tools.umcpCommand('computerroom/room/acquire', {
				room: room
			}).then(lang.hitch(this, function() {
				return this.umcpCommand('computerroom/query').then(lang.hitch(this, function(response) {
					this._initGridData(response.result);
					this._lastUpdate = new Date();
					this._firstUpdate = new Date();
//					this.standby(true);
					this._updateRooms();
				}));
			})));
		},

		onReboot: function(computers) {
			// event stub
		},

		getComputersForReboot: function() {
			// get all connected computers
			var computers = [];
			this.moduleStore.query().forEach(function(iitem) {
				// only take connected computers and computers where no teacher is logged in
				if (iitem.connection == 'connected' && !iitem.teacher) {
					computers.push(iitem);
				}
			});
			return computers;
		},

		reboot: function(computers) {
			// switch the computers on and update the progress of a Deferred
			// do not reboot all computers at once, use an offset of 300ms
			if (computers === undefined) {
				var computers = this.getComputersForReboot();
			}
			var deferred = new Deferred();
			var percentPerItem = 100.0 / (computers.length + 1);
			this.computersWereRestarted = true;
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
					// query for the given item (teacher computers have been filtered out!)
					this.moduleStore.query({
						id: item.id
					}).forEach(lang.hitch(this, function(currentItem) {
						// found the item -> update it with new information
						this.moduleStore.put(lang.mixin({}, currentItem, item));
					}));

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
