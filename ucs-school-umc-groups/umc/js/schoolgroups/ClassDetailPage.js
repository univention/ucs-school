/*
 * SPDX-FileCopyrightText: 2015-2025 Univention GmbH
 * SPDX-License-Identifier: AGPL-3.0-only
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"umc/widgets/MultiObjectSelect",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/modules/schoolgroups/DetailPage",
	"umc/i18n!umc/modules/schoolgroups"
], function(declare, lang, MultiObjectSelect, TextBox, ComboBox, DetailPage, _) {

	return declare("umc.modules.schoolgroups.ClassDetailPage", [DetailPage], {
		getWidgets: function() {
			return [{
				type: ComboBox,
				name: 'school',
				label: _('School'),
				staticValues: []
			}, {
				type: TextBox,
				name: 'name',
				label: _('Class'),
				disabled: true
			}, {
				type: TextBox,
				name: 'description',
				label: _('Description'),
				disabled: true
			}, this.getMultiSelectWidget()];
		},

		getMultiSelectWidget: function() {
			return lang.mixin(this.inherited(arguments), {
				label: _('Teachers'),
				description: _('List of teachers which are member of the specified class'),
				queryOptions: function() {
					return { group: 'teacher' };
				}
			});
		},

		getMultiSelectGroup: function() {
			return lang.mixin(this.inherited(arguments), {
				staticValues: [{id: 'teacher', label: _('All teachers')}]
			});
		}

	});
});
