/*
 * Copyright 2018-2020 Univention GmbH
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
	"umc/i18n/tools",
	"umc/i18n!umc/modules/schoollists"
], function(declare, lang, array, on, locale, Deferred, Dialog, entities, dialog, tools, Module,
			Grid, Page, Form, SearchBox, TextBox, ComboBox, CheckBox, Button, Text, ContainerWidget, ProgressInfo,
			SearchForm, i18nTools, _) {

	return declare("umc.modules.schoollists", [ Module ], {
		idProperty: 'id',
		_searchPage: null,
		_csvFormat: 'excel',

		convert2UTF16le: function(str) {
			// Convert function from https://developers.google.com/web/updates/2012/06/How-to-convert-ArrayBuffer-to-and-from-String
			var buf = new ArrayBuffer(str.length*2); // 2 bytes for each char
			var bufView = new Uint16Array(buf);
			for (var i=0, strLen=str.length; i < strLen; i++) {
				bufView[i] = str.charCodeAt(i);
			}
			return buf;
		},

		getCsvBlob: function(encoding, result) {
			var csv;
			var utfBom = "\uFEFF";
			if (encoding === 'utf16le') {
				csv = this.convert2UTF16le(utfBom + result.result.csv);
			} else {
				csv = result.result.csv;
			}
			return new Blob([csv], {type: 'text/csv'});
		},

		openDownload: function(result) {
			var blob = this.getCsvBlob(this._csvFormat === 'excel' ? 'utf16le' : 'utf8', result);
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
				helpText: _(
					'This module lets you export class and workgroup lists. The lists are in the CSV format. ' +
					'If you have problems opening the exported file, ensure the encoding is set to UTF-16 ' +
					'and the field separator is set to tabs.' +
					"<p><a target='_blank' href=modules/schoollists/lo_import_hl_en.png>Help for LibreOffice</a></p>" +
					"<p>If you can't open that file you can try to export the list in an alternative format " +
					'which is UTF-8 encoded and uses commas as field separators.</p>'
				)
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
				dynamicValues: 'schoollists/schools'
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
				}
			}, {
				type: Button,
				name: 'csvUtf16',
				description: _('Download a list of group members'),
				label: _('Export (Recommended)'),
				style: "margin: 0; width: 30em;",
				onClick: lang.hitch(this, function() {
					if (this._searchForm.validate()) {
						this._csvFormat = 'excel';
						this._searchForm.submit();
					} else {
						dialog.alert(_('Please select a class or workgroup.'));
					}
				})
			}, {
				type: Button,
				name: 'csvUtf8',
				description: _('Download a list of group members (in an alternative format)'),
				label: _('Export (Alternative format)'),
				style: "margin: 0; width: 30em;",
				onClick: lang.hitch(this, function() {
					if (this._searchForm.validate()) {
						this._csvFormat = 'alternative';
						this._searchForm.submit();
					} else {
						dialog.alert(_('Please select a class or workgroup.'));
					}
				})
			}];

			var layout = [
				['school', 'group'],
				['csvUtf16'],
				['csvUtf8']
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
						separator: this._csvFormat === 'excel' ? '\t' : ','
					}).then(lang.hitch(this, 'openDownload'));
				})
			});
			var container = new ContainerWidget();
			container.addChild(this._searchForm);
			this._searchPage.addChild(container);
			this._searchForm.ready().then(lang.hitch(this, 'standby', false));

		}
	});

});
