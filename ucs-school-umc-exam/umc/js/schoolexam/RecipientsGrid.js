/*
 * Copyright 2013-2024 Univention GmbH
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
/*global require,define,window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/store/Observable",
	"dojo/store/Memory",
	"umc/widgets/Grid",
	"umc/widgets/Text",
	"umc/i18n!umc/modules/schoolexam"
], function(declare, lang, Observable, Memory, Grid, Text, _) {
	return declare("umc.modules.schoolexam.RecipientsGrid", [Grid], {
		/**
		 * This grid lists all students, that are members of a provided list of groups (classes, working groups)
		 */
		constructor: function() {
			this.gridOptions = {
				selectionMode: 'none'
			};
			this.moduleStore = new Observable(new Memory({ data: [], idProperty: 'dn' }));
			this.actions = [];
			this.columns = [
				{
					name: 'name',
					label: _('Name'),
					formatter: function(value, user) {
						return user.firstname + ' ' + user.lastname
					}
				},
				{
					name: 'school_classes',
					label: _('School classes'),
					formatter: function(value, user) {
						return user['school_classes'].join(', ');
					}
				}
			]
		},
		setGroups: function(groups, examwizard) {
			/**
			 * Updates the grid with a new set of groups and thus a new set of students to display. This function
			 * fetches data via an umc call.
			 */
			if (groups.length === 0) {
				this.moduleStore.query().forEach(lang.hitch(this, function(user) {
					this.moduleStore.remove(user.dn)
				}))
			} else {
				this.umcpCommand('schoolexam/groups2students', {groups: groups}).then(lang.hitch(this, function(response) {
					var newUsers = {};
					response.result.forEach(function(user) {
						newUsers[user.dn] = user;
					});
					this.moduleStore.query().forEach(lang.hitch(this, function(user) {
						if (newUsers[user.dn]) {
							this.moduleStore.put(newUsers[user.dn], {overwrite: true});
							delete newUsers[user.dn]
						} else {
							this.moduleStore.remove(user.dn);
						}
					}));
					Object.keys(newUsers).forEach(lang.hitch(this, function(dn) {
						this.moduleStore.add(newUsers[dn])
					}));
					this.update();
				}), lang.hitch(
                    this,
                    function(error) {
                        vals = examwizard._pages.advanced._form.value
                        vals.recipients = []
                        examwizard._pages.advanced._form.set("value", vals);
                }))
			}
		}
	})
});
