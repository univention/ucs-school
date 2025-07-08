/*
 * SPDX-FileCopyrightText: 2014-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */

/*global define window*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"dojo/topic",
	"dojo/Deferred",
	"dojox/html/entities",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/SearchBox",
	"umc/modules/schoolwizards/SchoolWizard",
	"umc/modules/schoolwizards/Grid",
	"umc/i18n!umc/modules/schoolwizards"
], function(declare, lang, array, topic, Deferred, entities, tools, dialog, SearchBox, SchoolWizard, Grid, _) {

	return declare("umc.modules.schoolwizards.SchoolGrid", [Grid], {

		headerText: _('Management of schools'),
		helpText: '',
		objectNamePlural: _('schools'),
		objectNameSingular: _('school'),
		firstObject: _('the first school'),
		createObjectWizard: SchoolWizard,
		sortFields: ['display_name'],
		singleMasterDeferred: null,

		postMixInProperties: function() {
			this.inherited(arguments);
			this.school = this.$dn$;
			this.singleMasterDeferred = new Deferred();
			this.umcpCommand('schoolwizards/schools/singlemaster').then(lang.hitch(this, function(data) {
				this.singleMasterDeferred.resolve(data.result);
			}));
		},

		getGridColumns: function() {
			return [{
				name: 'display_name',
				label: _('Name of the school')
			}, {
				name: 'name',
				label: _('School abbreviation')
			}, {
				name: 'educational_servers',
				label: _('Educational servers'),
				formatter: lang.hitch(this, '_serverDnFormatter')
			}, {
				name: 'administrative_servers',
				label: _('Administrative servers'),
				formatter: lang.hitch(this, '_serverDnFormatter')
			}];
		},

		_serverDnFormatter: function(dns) {
			return array.map(dns, function(dn) {
				return tools.explodeDn(dn, true)[0];
			}).join(', ');
		},

		getObjectIdName: function(item) {
			return item.display_name;
		},

		createWizard: function(props) {
			var originalArguments = arguments;
			this.standbyDuring(this.singleMasterDeferred);
			this.singleMasterDeferred.then(lang.hitch(this, function(singleMaster) {
				props.singleMaster = singleMaster;
				this.inherited(originalArguments);
			}));
		},

		getSearchWidgets: function() {
			return [{
				type: SearchBox,
				'class': 'umcTextBoxOnBody',
				name: 'filter',
				label: _('Filter'),
				inlineLabel: _('Search...'),
				onSearch: lang.hitch(this, function() {
					this._searchForm.submit();
				})
			}];
		},

		getSearchLayout: function() {
			return [['filter']];
		},

		getDeleteConfirmMessage: function(objects) {
			var msg;
			if (objects.length === 1) {
				var school = objects[0];
				msg = _('Please confirm to delete the school "%(displayName)s" (%(name)s).', {displayName: entities.encode(school.display_name), name: entities.encode(school.name)});
			} else {
				msg = _('Please confirm to delete the following schools:');
				msg += '<ul>';
				array.forEach(objects, function(school) {
					msg += lang.replace('<li>"{displayName}" ({name})</li>', {displayName: entities.encode(school.display_name), name: entities.encode(school.name)});
				});
				msg += '</ul>';
			}
			msg += '<br/><br/>';
			msg += '<strong>' + _('Warning') + ':</strong> ';
			msg += _('Deleting schools will also delete every teacher and student.') + '<br/>' + _('This action cannot be undone.');
			return msg;
		},

		deleteObjects: function(ids, objects) {
			var deferred = this.inherited(arguments);
			deferred.then(lang.hitch(this, function() {
				this.relogin();
			}));
			return deferred;
		},

		relogin: function() {
			// copied from umc/app.js with different wording
			dialog.confirm(_('After deleting a school it is recommended to start with a new session. A list of all schools was saved at the beginning in various places which is now outdated. This may result in (harmless but annoying) error messages. Do you want to logout?'), [{
				label: _('Cancel')
			}, {
				label: _('Logout'),
				'default': true,
				callback: lang.hitch(this, function() {
					topic.publish('/umc/actions', 'session', 'logout');
					tools.closeSession();
					window.location.reload(true);
				})
			}]);
		}
	});
});
