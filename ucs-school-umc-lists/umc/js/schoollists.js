/*
 * Copyright 2018 Univention GmbH
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
	"dojo/on",
	"dojo/date/locale",
	"dojo/Deferred",
	"dijit/Dialog",
	"dojox/html/entities",
	"umc/dialog",
	"umc/tools",
	"umc/widgets/Module",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/Form",
	"umc/widgets/SearchBox",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/widgets/CheckBox",
	"umc/widgets/Button",
	"umc/widgets/Text",
	"umc/widgets/ContainerWidget",
	"umc/widgets/ProgressInfo",
	"umc/widgets/SearchForm",
	"umc/i18n!umc/modules/schoollists"
], function(declare, lang, array, on, locale, Deferred, Dialog, entities, dialog, tools, Module,
            Grid, Page, Form, SearchBox, TextBox, ComboBox, CheckBox, Button, Text, ContainerWidget, ProgressInfo, SearchForm, _) {

	return declare("umc.modules.schoollists", [ Module ], {
		idProperty: 'id',
		_searchPage: null,
		openDownload: function(result) {
			var blob = new Blob([result.result.csv], {type: 'text/csv'});
			var url = URL.createObjectURL(blob);
			if (window.navigator && window.navigator.msSaveOrOpenBlob) {
				// IE doesn't open objectURLs directly
				window.navigator.msSaveOrOpenBlob(blob, result.result.filename);
				return;
			}

			var link = document.createElement('a');
			link.style = "display: none";
			document.body.appendChild(link);
			link.href = url;
			link.download = result.result.filename;
			link.click();
			link.remove();
		},

		buildRendering: function() {
			this.inherited(arguments);

			this.standby(true);

			this._searchPage = new Page({
				fullWidth: true,
				headerText: this.description,
				helpText: ''
			});

			this.addChild(this._searchPage);

			var widgets = [{
				type: ComboBox,
				name: 'school',
				description: _('Select the school.'),
				label: _('School'),
				autoHide: true,
				size: 'TwoThirds',
				required: true,
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				dynamicValues: 'schoollists/schools',
			}, {
				type: ComboBox,
				name: 'group',
				required: true,
				description: _('Select a class or workgroup.'),
				label: _('Class or workgroup'),
				dynamicValues: 'schoollists/groups',
				umcpCommand: lang.hitch(this, 'umcpCommand'),
				depends: 'school',
				onValuesLoaded: function() {
					this.set('value', null);
				},
			}, {
				type: Button,
				name: 'csv',
				description: _('Download a list of group members'),
				label: 'CSV',
				onClick: lang.hitch(this, function() {
					if (this._searchForm.validate()) {
						this._searchForm.submit();
					} else {
						dialog.alert(_('Please select a class or workgroup.'));
					}
				}),
			}];

			var layout = [
				[ 'school', 'group', 'csv' ]
			];

			this._searchForm = new SearchForm({
				region: 'top',
				hideSubmitButton: true,
				widgets: widgets,
				layout: layout,
				onSearch: lang.hitch(this, function(values) {
					this.umcpCommand('schoollists/csvlist', {
						school: values.school,
						group: values.group,
					}).then(lang.hitch(this, 'openDownload'));
				})
			});

			this._searchPage.addChild(this._searchForm);
			this._searchForm.ready().then(lang.hitch(this, 'standby', false));

		}
	});

});
