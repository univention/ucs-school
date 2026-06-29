/*
 * SPDX-FileCopyrightText: 2013-2026 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global require,define,window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojox/html/entities",
	"dojo/store/Observable",
	"dojo/store/Memory",
	"umc/widgets/Grid",
	"umc/widgets/Text",
	"umc/widgets/Tooltip",
	"umc/i18n!umc/modules/schoolexam"
], function(declare, lang, entities, Observable, Memory, Grid, Text, Tooltip, _) { // eslint-disable-line max-params
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
						return entities.encode(user.firstname + ' ' + user.lastname);
					}
				},
				{
					name: 'school_classes',
					label: _('School classes'),
					formatter: lang.hitch(this, function(value, user) {
						// language-aware sort; numeric so '2a' sorts before '10a'
						const classes = (user['school_classes'] || []).slice().sort(function(a, b) {
							return a.localeCompare(b, undefined, {numeric: true});
						});
						const content = classes.join(', ');
						const widget = new Text({
							content: entities.encode(content)
						});
						this.own(widget);
						// the cell truncates with an ellipsis; the tooltip shows the full list
						if (content) {
							const tooltip = new Tooltip({
								label: entities.encode(content),
								connectId: [widget.domNode],
								position: ['below', 'above']
							});
							widget.own(tooltip);
						}
						return widget;
					})
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
