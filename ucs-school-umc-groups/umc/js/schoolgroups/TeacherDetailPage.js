/*
 * SPDX-FileCopyrightText: 2015-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/_base/array",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolgroups/DetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, array, MultiObjectSelect, TextBox, ComboBox, DetailPage, _) {

	return declare("umc.modules.schoolgroups.TeacherDetailPage", [DetailPage], {
		multiWidgetName: 'classes',
		getWidgets: function() {
			return [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				staticValues: []
			}, {
				type: TextBox,
				name: 'name',
				label: _('Teacher'),
				disabled: true
			}, this.getMultiSelectWidget()];
		},

		getMultiSelectWidget: function() {
			return lang.mixin(this.inherited(arguments), {
				label: _('Classes'),
				description: _('List of classes which the selected teacher is member of'),
				formatter: function(items) {
					array.forEach(items, function(schoolClass) {
						if (typeof(schoolClass) === 'object' && schoolClass.hasOwnProperty('label') && schoolClass.hasOwnProperty('school')) {
							if (! schoolClass.hasOwnProperty('shortName')) {
								schoolClass.shortName = schoolClass.label;
							}
							schoolClass.label = schoolClass.shortName + ' (' + schoolClass.school + ')';
						}
					});
					return items;
				},
				queryCommand: lang.hitch(this, function(options) {
					var school = this._form.getWidget(this.multiWidgetName)._detailDialog._form.getWidget('school').get('value');
					return this.umcpCommand('schoolgroups/classes', options).then(function(data) {
						array.forEach(data.result, function(schoolClass) {
							schoolClass.school = school;
						});
						return data.result;
					});
				})
			});
		},

		getMultiSelectGroup: function() {
			return null;
		},

		load: function() {
			// Loading a teacher into this form sets the school to the teachers primary school.
			var currentSchoolChoice = this._form.getWidget('school').get('value');
			this.inherited(arguments).then(lang.hitch(this, function(){
				this._form.getWidget('school').set('value', currentSchoolChoice);
			}));
		},
	});
});
